"""Convert suitable inline enumerations into markdown lists (Phase 5D)."""

from __future__ import annotations

import re

_INLINE_ENUM_RE = re.compile(
    r"^(?P<head>.{0,80}?\b(?:include|includes|are|consist of|comprises?)\s+)"
    r"(?P<body>[A-Z][^.]{10,220}?)\.\s*$"
)
_SPLIT_ITEMS_RE = re.compile(r"\s*,\s*|\s+,?\s+and\s+", re.I)


def _split_enum_items(body: str) -> list[str]:
    parts = [part.strip(" .;") for part in _SPLIT_ITEMS_RE.split(body) if part.strip()]
    # Keep only short noun-phrase style items.
    items = [part for part in parts if 2 <= len(part) <= 80 and "\n" not in part]
    return items


def convert_inline_lists(markdown: str) -> str:
    """Turn 'X includes A, B, and C.' into a short bullet list when helpful."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(("#", "|", ">", "-", "*", "•", "✔", "1.", "`", "└", "↓"))
            or re.match(r"^\d+\.\s", stripped)
        ):
            out.append(line)
            continue

        match = _INLINE_ENUM_RE.match(stripped)
        if not match:
            out.append(line)
            continue
        items = _split_enum_items(match.group("body"))
        if len(items) < 3:
            out.append(line)
            continue
        head = match.group("head").rstrip()
        out.append(head)
        out.append("")
        for item in items:
            out.append(f"- {item}")
        out.append("")
    return "\n".join(out)
