"""Normalize markdown tables for consistent rendering (Phase 5E)."""

from __future__ import annotations

import re

_TABLE_LINE_RE = re.compile(r"^\s*\|")
_SEP_CELL_RE = re.compile(r"^:?-+:?$")


def normalize_tables(markdown: str) -> str:
    """
    Fix common table issues: uneven pipes, missing separator row, ragged columns.

    Does not invent cell values; pads empty cells only to keep column counts aligned.
    """
    lines = (markdown or "").splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not _TABLE_LINE_RE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue

        block: list[str] = []
        while i < len(lines) and _TABLE_LINE_RE.match(lines[i]):
            block.append(lines[i].rstrip())
            i += 1

        fixed = _normalize_table_block(block)
        if fixed:
            if out and out[-1].strip():
                out.append("")
            out.extend(fixed)
            if i < len(lines) and lines[i].strip():
                out.append("")
        # else: drop empty/malformed table entirely

    return "\n".join(out).rstrip()


def _split_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(_SEP_CELL_RE.match(cell.replace(" ", "")) for cell in cells)


def _normalize_table_block(block: list[str]) -> list[str]:
    if not block:
        return []

    rows = [_split_row(line) for line in block]
    # Drop completely empty rows.
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return []

    width = max(len(row) for row in rows)
    if width < 1:
        return []

    padded = [row + [""] * (width - len(row)) for row in rows]

    # Ensure separator after header.
    if len(padded) == 1:
        # Header-only → not a useful table.
        return []
    if not _is_separator_row(padded[1]):
        sep = ["---"] * width
        padded.insert(1, sep)
    else:
        padded[1] = ["---"] * width

    # Header + separator only → empty table.
    data_rows = padded[2:]
    if not data_rows or not any(any(cell.strip() for cell in row) for row in data_rows):
        return []

    # Align cell widths for readability (cap for very wide content).
    col_widths = [0] * width
    for row in padded:
        for idx, cell in enumerate(row):
            col_widths[idx] = min(max(col_widths[idx], len(cell)), 48)

    rendered: list[str] = []
    for row_idx, row in enumerate(padded):
        if row_idx == 1:
            cells = ["-" * max(3, col_widths[idx]) for idx in range(width)]
        else:
            cells = [row[idx].ljust(col_widths[idx]) for idx in range(width)]
        rendered.append("| " + " | ".join(cells) + " |")
    return rendered
