"""Remove empty major sections from rendered markdown (Phase 5E)."""

from __future__ import annotations

import re

_SECTION_SPLIT_RE = re.compile(r"(?m)^(#{2,3}\s+.+)$")
_EMPTYISH_RE = re.compile(
    r"^(\s*|_(?:none|no [^.]+|empty)\.?_|\(none\)|\(not available\))\s*$",
    re.I,
)


def _is_meaningful(body: str) -> bool:
    text = (body or "").strip()
    if not text:
        return False
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and line.strip() != "---"
    ]
    if not lines:
        return False
    if all(_EMPTYISH_RE.match(line) for line in lines):
        return False
    table_lines = [line for line in lines if line.startswith("|")]
    if table_lines and len(table_lines) == len(lines):
        # Header + separator only (no data rows) is empty.
        if len(table_lines) <= 1:
            return False
        sep = table_lines[1].replace("|", "").replace(":", "").replace("-", "").strip()
        if not sep and len(table_lines) == 2:
            return False
    return True


def remove_empty_sections(markdown: str) -> tuple[str, int]:
    """Drop ##/### sections whose bodies have no meaningful content.

    Returns (cleaned_markdown, removed_count).
    """
    text = markdown or ""
    parts = _SECTION_SPLIT_RE.split(text)
    if len(parts) == 1:
        return text.strip(), 0

    out: list[str] = []
    removed = 0
    preamble = parts[0].strip("\n")
    if preamble.strip():
        out.append(preamble.rstrip())

    index = 1
    while index < len(parts):
        heading = parts[index].strip()
        body = parts[index + 1] if index + 1 < len(parts) else ""
        if _is_meaningful(body):
            if out:
                out.append("")
            out.append(heading)
            cleaned_body = body.strip("\n")
            if cleaned_body:
                out.append("")
                out.append(cleaned_body)
        else:
            removed += 1
        index += 2

    return "\n".join(out).strip(), removed
