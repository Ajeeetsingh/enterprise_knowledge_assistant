"""Post-process generated PDFs: cover, header/footer, bookmarks, metadata."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from toolkit.config import ToolkitConfig
from toolkit.manifest import _extract_markdown_metadata

logger = logging.getLogger(__name__)

# Two-column markdown table rows: | Field | Value |
_FIELD_RE = re.compile(
    r"^\|\s*\*{0,2}(?P<field>[^*|\n]+?)\*{0,2}\s*\|\s*(?P<value>.+?)\s*\|\s*$",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def enhance_and_validate_pdf(
    pdf_path: Path,
    *,
    markdown_path: Path,
    config: ToolkitConfig,
) -> None:
    """Apply enterprise cover/header/footer/bookmarks/metadata and soft-validate.

    Never raises for enhancement/validation issues — logs warnings only.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed; skipping PDF enterprise enhancements")
        return

    meta = _resolve_document_meta(markdown_path)
    producer = _producer_label(config.pdf_engine)
    headings = _parse_markdown_headings(markdown_path)

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not open PDF for enhancement (%s): %s", pdf_path.name, exc)
        return

    try:
        cover_enabled = config.cover_page
        bookmarks_enabled = config.bookmarks

        if cover_enabled:
            _insert_cover_page(doc, meta=meta)

        if config.header_enabled or config.footer_enabled or config.page_numbers:
            _stamp_header_footer(
                doc,
                title=meta["title"],
                classification_label=meta["classification_label"],
                header_enabled=config.header_enabled,
                footer_enabled=config.footer_enabled,
                page_numbers=config.page_numbers,
                skip_cover=cover_enabled,
            )

        if bookmarks_enabled:
            _apply_bookmarks(doc, headings=headings, skip_cover=cover_enabled)

        if config.pdf_metadata:
            _apply_metadata(doc, meta=meta, producer=producer)

        tmp = pdf_path.with_suffix(".pdf.tmp")
        doc.save(tmp, garbage=3, deflate=True)
        doc.close()
        tmp.replace(pdf_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF enhancement failed for %s: %s", pdf_path.name, exc)
        try:
            doc.close()
        except Exception:  # noqa: BLE001
            pass
        tmp = pdf_path.with_suffix(".pdf.tmp")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return

    if config.enterprise_checks:
        _soft_validate(
            pdf_path,
            title=meta["title"],
            classification_label=meta["classification_label"],
            expect_header=config.header_enabled,
            expect_footer=config.footer_enabled or config.page_numbers,
            expect_metadata=config.pdf_metadata,
            expect_toc_links=config.toc_links and config.toc,
            expect_cover=config.cover_page,
            expect_bookmarks=config.bookmarks,
        )


def _resolve_document_meta(markdown_path: Path) -> dict[str, Any]:
    extracted = _extract_markdown_metadata(markdown_path)
    title = extracted.get("title") or _title_from_filename(markdown_path.name)

    fields = _parse_metadata_table(markdown_path)
    classification_label = (
        fields.get("classification")
        or fields.get("confidentiality")
        or extracted.get("classification")
        or ""
    )
    if classification_label and len(classification_label) <= 3 and classification_label.upper().startswith("C"):
        classification_label = f"Internal ({classification_label.upper()})"

    keywords = fields.get("keywords")
    if not keywords:
        keywords = _default_keywords(title, classification_label)

    return {
        "title": title,
        "metadata_title": _metadata_title(title),
        "document_id": fields.get("document id") or extracted.get("document_id") or "",
        "version": fields.get("version") or "",
        "classification_label": classification_label,
        "owner": fields.get("owner") or "",
        "approver": fields.get("approver") or "",
        "effective_date": fields.get("effective date") or "",
        "keywords": keywords,
    }


def _parse_metadata_table(markdown_path: Path) -> dict[str, str]:
    """Parse Field/Value rows from the document metadata table (head of file only)."""
    out: dict[str, str] = {}
    try:
        head = markdown_path.read_text(encoding="utf-8", errors="replace")[:16000]
    except OSError:
        return out

    skip_fields = {"field", "---|---", "---"}
    for line in head.splitlines():
        match = _FIELD_RE.match(line.strip())
        if not match:
            continue
        key = re.sub(r"\s+", " ", match.group("field")).strip().lower()
        value = match.group("value").strip()
        # Strip optional surrounding backticks from scalar cells
        if value.startswith("`") and value.endswith("`") and value.count("`") == 2:
            value = value[1:-1].strip()
        if not key or not value or key in skip_fields or key.startswith("---"):
            continue
        if key not in out:
            out[key] = value
    return out


def _parse_markdown_headings(markdown_path: Path) -> list[tuple[int, str]]:
    try:
        text = markdown_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    headings: list[tuple[int, str]] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        # Skip decorative rules mistaken as headings
        if title.startswith("---") or title.startswith("|"):
            continue
        headings.append((level, title))
    return headings


def _title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"^\d+_", "", stem)
    return stem.replace("_", " ").strip().title() or filename


def _metadata_title(title: str) -> str:
    if title.lower().startswith("apex national bank"):
        return title
    return f"Apex National Bank — {title}"


def _default_keywords(title: str, classification_label: str) -> str:
    parts = ["ANB", "Banking", "Enterprise"]
    if "Internal" in classification_label:
        parts.append("Internal")
    elif classification_label:
        parts.append(classification_label.split("(")[0].strip())
    if title:
        parts.append(title)
    return ", ".join(parts)


def _producer_label(engine: str) -> str:
    eng = engine.lower()
    if eng in {"xelatex", "lualatex", "pdflatex", "latex", "tectonic"}:
        return "Pandoc + XeLaTeX"
    if eng in {"chrome", "chromium", "edge", "msedge"}:
        return "Pandoc + Chrome"
    if eng == "weasyprint":
        return "Pandoc + WeasyPrint"
    return f"Pandoc + {engine}"


def _wrap_text(text: str, *, fontname: str, fontsize: float, max_width: float) -> list[str]:
    """Simple word wrap for cover-page field values."""
    import fitz

    if not text:
        return [""]
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _insert_cover_page(doc: Any, *, meta: dict[str, Any]) -> None:
    import fitz

    # Match first content page size when available
    width, height = 595.0, 842.0  # A4
    if doc.page_count > 0:
        rect = doc[0].rect
        width, height = rect.width, rect.height

    cover = doc.new_page(pno=0, width=width, height=height)
    cx = width / 2

    def center_text(y: float, text: str, size: float, *, bold: bool = False) -> None:
        if not text:
            return
        font = "hebo" if bold else "helv"
        tw = fitz.get_text_length(text, fontname=font, fontsize=size)
        cover.insert_text(
            fitz.Point(cx - tw / 2, y),
            text,
            fontname=font,
            fontsize=size,
            color=(0.12, 0.12, 0.12),
        )

    center_text(160, "Apex National Bank", 16, bold=True)
    center_text(230, meta["title"].upper(), 22, bold=True)
    center_text(270, "Enterprise Reference Document", 12)

    # Divider
    cover.draw_line(
        fitz.Point(width * 0.22, 300),
        fitz.Point(width * 0.78, 300),
        color=(0.55, 0.55, 0.55),
        width=0.8,
    )

    rows = [
        ("Document ID", meta.get("document_id") or ""),
        ("Version", meta.get("version") or ""),
        ("Classification", meta.get("classification_label") or ""),
        ("Owner", meta.get("owner") or ""),
        ("Approver", meta.get("approver") or ""),
        ("Effective Date", meta.get("effective_date") or ""),
    ]

    y = 360
    label_x = width * 0.22
    value_x = width * 0.42
    value_max_width = width * 0.78 - value_x
    for label, value in rows:
        cover.insert_text(
            fitz.Point(label_x, y),
            f"{label}:",
            fontname="hebo",
            fontsize=10,
            color=(0.2, 0.2, 0.2),
        )
        lines = _wrap_text(value, fontname="helv", fontsize=10, max_width=value_max_width)
        for i, line in enumerate(lines or [""]):
            cover.insert_text(
                fitz.Point(value_x, y + i * 14),
                line,
                fontname="helv",
                fontsize=10,
                color=(0.15, 0.15, 0.15),
            )
        y += max(28, 14 * max(len(lines), 1) + 10)


def _stamp_header_footer(
    doc: Any,
    *,
    title: str,
    classification_label: str,
    header_enabled: bool,
    footer_enabled: bool,
    page_numbers: bool,
    skip_cover: bool,
) -> None:
    import fitz

    start = 1 if skip_cover and doc.page_count > 1 else 0
    content_pages = max(doc.page_count - start, 0)
    display_title = title if len(title) <= 90 else title[:87] + "..."
    left_margin = 40
    font = "helv"
    size = 8
    color = (0.15, 0.15, 0.15)
    rule = (0.55, 0.55, 0.55)

    for index in range(start, doc.page_count):
        page = doc[index]
        width, height = page.rect.width, page.rect.height
        content_index = index - start + 1  # 1-based among content pages

        if header_enabled:
            page.insert_text(
                fitz.Point(left_margin, 22),
                "Apex National Bank",
                fontname=font,
                fontsize=size,
                color=color,
            )
            page.insert_text(
                fitz.Point(left_margin, 34),
                display_title,
                fontname=font,
                fontsize=size,
                color=color,
            )
            page.draw_line(
                fitz.Point(left_margin, 40),
                fitz.Point(width - left_margin, 40),
                color=rule,
                width=0.6,
            )

        if footer_enabled or page_numbers:
            page.draw_line(
                fitz.Point(left_margin, height - 32),
                fitz.Point(width - left_margin, height - 32),
                color=rule,
                width=0.6,
            )
            if footer_enabled:
                page.insert_text(
                    fitz.Point(left_margin, height - 18),
                    classification_label,
                    fontname=font,
                    fontsize=size,
                    color=color,
                )
            if page_numbers and content_pages > 0:
                label = f"Page {content_index} of {content_pages}"
                text_width = fitz.get_text_length(label, fontname=font, fontsize=size)
                page.insert_text(
                    fitz.Point(width - left_margin - text_width, height - 18),
                    label,
                    fontname=font,
                    fontsize=size,
                    color=color,
                )


def _apply_bookmarks(
    doc: Any,
    *,
    headings: list[tuple[int, str]],
    skip_cover: bool,
) -> None:
    """Build PDF outline from markdown headings by locating text on pages."""
    if not headings or doc.page_count == 0:
        return

    start = 1 if skip_cover and doc.page_count > 1 else 0
    toc: list[list[Any]] = []
    search_from = start

    for level, title in headings:
        # Normalize search needle (strip markdown emphasis)
        needle = re.sub(r"[*_`]+", "", title).strip()
        if len(needle) < 2:
            continue
        page_found: int | None = None
        # Prefer forward search so outline order matches document order
        for page_idx in range(search_from, doc.page_count):
            try:
                hits = doc[page_idx].search_for(needle[:120])
            except Exception:  # noqa: BLE001
                hits = []
            if hits:
                page_found = page_idx
                search_from = page_idx
                break
        if page_found is None:
            # Fallback: scan all content pages
            for page_idx in range(start, doc.page_count):
                try:
                    hits = doc[page_idx].search_for(needle[:120])
                except Exception:  # noqa: BLE001
                    hits = []
                if hits:
                    page_found = page_idx
                    break
        if page_found is None:
            continue
        # PyMuPDF TOC page numbers are 1-based
        toc.append([level, needle, page_found + 1])

    if toc:
        try:
            doc.set_toc(toc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not set PDF bookmarks: %s", exc)


def _apply_metadata(doc: Any, *, meta: dict[str, Any], producer: str) -> None:
    now = datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    doc.set_metadata(
        {
            "title": meta.get("metadata_title") or meta.get("title") or "",
            "author": "Apex National Bank",
            "subject": "Enterprise Reference Document",
            "keywords": meta.get("keywords") or "",
            "creator": "benchmark_dataset_toolkit",
            "producer": producer,
            "creationDate": now,
            "modDate": now,
        }
    )


def _soft_validate(
    pdf_path: Path,
    *,
    title: str,
    classification_label: str,
    expect_header: bool,
    expect_footer: bool,
    expect_metadata: bool,
    expect_toc_links: bool,
    expect_cover: bool,
    expect_bookmarks: bool,
) -> None:
    try:
        import fitz
    except ImportError:
        return

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Validation skipped (unreadable PDF %s): %s", pdf_path.name, exc)
        return

    try:
        if doc.page_count < 1:
            logger.warning("Validation: %s has no pages", pdf_path.name)
            return

        cover_text = doc[0].get_text("text") or ""
        content_idx = 1 if expect_cover and doc.page_count > 1 else 0
        content = doc[content_idx]
        content_text = content.get_text("text") or ""

        if expect_cover:
            if "Apex National Bank" not in cover_text:
                logger.warning("Validation: cover bank name missing in %s", pdf_path.name)
            if "Enterprise Reference Document" not in cover_text:
                logger.warning("Validation: cover subtitle missing in %s", pdf_path.name)
            if "Page 1 of" in cover_text:
                logger.warning("Validation: cover page should not show page numbers in %s", pdf_path.name)

        if expect_header and doc.page_count > content_idx:
            if "Apex National Bank" not in content_text:
                logger.warning("Validation: header bank name missing on content page of %s", pdf_path.name)

        if expect_footer and doc.page_count > content_idx:
            if classification_label.split("(")[0].strip() not in content_text and classification_label not in content_text:
                logger.warning("Validation: footer classification missing in %s", pdf_path.name)
            if "Page 1 of" not in content_text:
                logger.warning(
                    "Validation: content page numbering (Page 1 of N) missing in %s",
                    pdf_path.name,
                )

        if expect_metadata:
            md = doc.metadata or {}
            for key in ("title", "author", "subject", "creator", "producer"):
                if not (md.get(key) or "").strip():
                    logger.warning("Validation: PDF metadata '%s' empty in %s", key, pdf_path.name)

        if expect_toc_links:
            link_count = sum(len(page.get_links() or []) for page in doc)
            if link_count == 0:
                logger.warning("Validation: no TOC/internal hyperlinks in %s", pdf_path.name)

        if expect_bookmarks:
            toc = doc.get_toc() or []
            if not toc:
                logger.warning("Validation: PDF bookmarks/outline missing in %s", pdf_path.name)
    finally:
        doc.close()
