"""Build dataset_manifest.json for the Knowra benchmark evaluation framework."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from toolkit import __version__
from toolkit.models import ConversionResult, ConversionStatus
from toolkit.utils.paths import strip_leading_parts

logger = logging.getLogger(__name__)

_DOC_ID_RE = re.compile(
    r"\|\s*\*{0,2}Document\s+ID\*{0,2}\s*\|\s*`?([A-Z0-9][A-Z0-9\-_/]+)`?\s*\|",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(
    r"\|\s*\*{0,2}Document\s+Title\*{0,2}\s*\|\s*`?([^`|]+?)`?\s*\|",
    re.IGNORECASE,
)
_CLASS_RE = re.compile(
    r"\|\s*\*{0,2}Classification\*{0,2}\s*\|\s*`?([^`|]+?)`?\s*\|",
    re.IGNORECASE,
)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_CLASS_CODE_RE = re.compile(r"\b(C[0-4])\b", re.IGNORECASE)
_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page(?!\s*s)\b")


def default_manifest_path(output_dir: Path, repo_root: Path) -> Path:
    """Resolve ``benchmark/dataset_manifest.json`` from the repo layout."""
    benchmark_dir = repo_root / "benchmark"
    # Prefer sibling of pdf/ when output_dir is …/benchmark/pdf
    if output_dir.name.lower() == "pdf" and output_dir.parent.name.lower() == "benchmark":
        return (output_dir.parent / "dataset_manifest.json").resolve()
    return (benchmark_dir / "dataset_manifest.json").resolve()


def build_and_write_manifest(
    results: list[ConversionResult],
    *,
    output_dir: Path,
    strip_prefix: str,
    manifest_path: Path,
) -> Path | None:
    """Generate the dataset manifest from conversion results.

    Returns the written path, or None when nothing was written (e.g. dry-run).
    Never raises for per-document metadata failures.
    """
    documents: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda r: str(r.job.relative_source).lower()):
        if result.status == ConversionStatus.DRY_RUN:
            continue
        if result.status == ConversionStatus.FAILED and not result.job.target.is_file():
            continue
        if result.status in {ConversionStatus.SUCCESS, ConversionStatus.SKIPPED} or (
            result.job.target.is_file()
        ):
            try:
                documents.append(
                    _document_entry(result, output_dir=output_dir, strip_prefix=strip_prefix)
                )
            except Exception as exc:  # noqa: BLE001 — never fail the run for manifest rows
                logger.warning("Manifest entry skipped for %s: %s", result.job.source, exc)

    if not documents and all(r.status == ConversionStatus.DRY_RUN for r in results):
        logger.info("Skipping dataset_manifest.json (dry-run with no PDFs)")
        return None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": __version__,
        "total_documents": len(documents),
        "documents": documents,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    logger.info("Wrote dataset manifest → %s (%s documents)", manifest_path, len(documents))
    return manifest_path


def _document_entry(
    result: ConversionResult,
    *,
    output_dir: Path,
    strip_prefix: str,
) -> dict[str, Any]:
    source = result.job.source
    pdf = result.job.target

    rel_md = strip_leading_parts(result.job.relative_source, strip_prefix)
    if rel_md == Path("."):
        rel_md = Path(source.name)
    relative_markdown_path = rel_md.as_posix()

    try:
        relative_pdf_path = pdf.resolve().relative_to(output_dir.resolve()).as_posix()
    except ValueError:
        relative_pdf_path = pdf.name

    domain = relative_pdf_path.split("/", 1)[0] if "/" in relative_pdf_path else (
        relative_markdown_path.split("/", 1)[0] if "/" in relative_markdown_path else None
    )

    meta = _extract_markdown_metadata(source)

    file_size: int | None = None
    sha256: str | None = None
    last_modified: str | None = None
    page_count: int | None = None

    if pdf.is_file():
        try:
            stat = pdf.stat()
            file_size = int(stat.st_size)
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            pass
        sha256 = _sha256_file(pdf)
        page_count = _pdf_page_count(pdf)

    status = result.status.value
    if result.status == ConversionStatus.SUCCESS and not result.verified:
        status = "success"  # still list; verification is orthogonal

    return {
        "document_id": meta.get("document_id"),
        "title": meta.get("title"),
        "domain": domain,
        "relative_markdown_path": relative_markdown_path,
        "relative_pdf_path": relative_pdf_path,
        "classification": meta.get("classification"),
        "page_count": page_count,
        "file_size_bytes": file_size,
        "sha256": sha256,
        "last_modified": last_modified,
        "conversion_status": status,
    }


def _extract_markdown_metadata(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "document_id": None,
        "title": None,
        "classification": None,
    }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out

    # Limit scan to the metadata-heavy head of the document
    head = text[:12000]

    id_match = _DOC_ID_RE.search(head)
    if id_match:
        out["document_id"] = id_match.group(1).strip()

    title_match = _TITLE_RE.search(head)
    if title_match:
        out["title"] = _clean_title(title_match.group(1))
    else:
        h1 = _H1_RE.search(head)
        if h1:
            out["title"] = _clean_title(h1.group(1))

    class_match = _CLASS_RE.search(head)
    if class_match:
        raw = class_match.group(1).strip()
        code = _CLASS_CODE_RE.search(raw)
        out["classification"] = code.group(1).upper() if code else raw

    return out


def _clean_title(value: str) -> str:
    title = value.strip()
    # Strip leading "Apex National Bank — " noise when present in Document Title cells
    for prefix in ("Apex National Bank — ", "Apex National Bank - "):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
            break
    return title


def _sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _pdf_page_count(path: Path) -> int | None:
    """Best-effort page count without external PDF libraries."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.startswith(b"%PDF"):
        return None
    try:
        count = len(_PDF_PAGE_RE.findall(data))
        return count if count > 0 else None
    except Exception:  # noqa: BLE001
        return None
