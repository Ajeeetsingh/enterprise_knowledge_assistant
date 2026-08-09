"""Consistent Sources / Related Documents presentation (Phase 5E)."""

from __future__ import annotations

import re

_SECTION_RE = re.compile(
    r"(?ms)^(##\s+(Sources|Related Documents)\s*)\n(.*?)(?=^##\s+|\Z)"
)
_BULLET_RE = re.compile(r"^\s*[-*+•]\s+(.*)$")


def normalize_source_sections(markdown: str) -> str:
    """Deduplicate, alphabetically sort, and bullet-format Sources / Related Documents."""

    def _replace(match: re.Match[str]) -> str:
        heading = match.group(1).rstrip()
        body = match.group(3) or ""
        items = _extract_items(body)
        if not items:
            return ""
        bullets = "\n".join(f"- {item}" for item in items)
        return f"{heading}\n\n{bullets}\n"

    return _SECTION_RE.sub(_replace, markdown or "").strip()


def _extract_items(body: str) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        bullet = _BULLET_RE.match(line)
        text = bullet.group(1).strip() if bullet else line
        text = _clean_filename(text)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    items.sort(key=lambda value: value.lower())
    return items


def _clean_filename(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned.strip("*_`\"'")
