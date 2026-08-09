"""Heading hierarchy and duplicate cleanup (Phase 5E)."""

from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_headings(markdown: str) -> str:
    """
    Enforce # / ## / ### progression without skipped levels.

    Removes consecutive duplicate headings and duplicate ## section titles.
    """
    lines = (markdown or "").splitlines()
    out: list[str] = []
    last_level = 0
    last_text: str | None = None
    seen_major: set[str] = set()

    for line in lines:
        match = _HEADING_RE.match(line)
        if not match:
            out.append(line)
            continue

        level = len(match.group(1))
        text = match.group(2).strip()
        if not text:
            continue

        if level > 3:
            level = 3

        if last_level == 0:
            level = 1 if level == 1 else min(level, 2)
        else:
            if level > last_level + 1:
                level = last_level + 1
            level = max(1, min(level, 3))

        key = text.lower()
        if last_text and key == last_text.lower():
            continue
        if level == 2 and key in seen_major:
            continue

        out.append(f"{'#' * level} {text}")
        last_level = level
        last_text = text
        if level == 2:
            seen_major.add(key)

    return "\n".join(out)
