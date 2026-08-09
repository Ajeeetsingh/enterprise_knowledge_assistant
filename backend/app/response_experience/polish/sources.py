"""Clean, deduplicated Sources / Related Documents formatting (Phase 5D)."""

from __future__ import annotations

import re

_SOURCE_HEADINGS = {
    "sources",
    "related documents",
    "related standards",
    "related policies",
}


def _normalize_item(raw: str) -> str:
    item = raw.strip().strip("`")
    if item.lower().endswith(".pdf") or re.search(r"[\\/]", item):
        return f"`{item}`"
    return item


def clean_source_sections(markdown: str) -> str:
    """Deduplicate bullet items under Sources / Related* headings."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    in_source_section = False
    seen: set[str] = set()

    for line in lines:
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(1).strip().lower()
            in_source_section = title in _SOURCE_HEADINGS
            seen = set()
            out.append(line)
            continue

        if not in_source_section:
            out.append(line)
            continue

        bullet = re.match(r"^\s*[-*•]\s+(.+?)\s*$", line)
        if not bullet:
            out.append(line)
            continue
        item = _normalize_item(bullet.group(1))
        key = item.strip("`").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(f"- {item}")

    return "\n".join(out)
