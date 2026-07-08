"""Annotated line stream with page tracking."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAGE_MARKER_RE = re.compile(r"^<<<PAGE:(\d+)>>>$")


@dataclass(frozen=True)
class AnnotatedLine:
    """A single source line with structural context."""

    index: int
    text: str
    raw_text: str
    indent: int
    page: int | None
    is_blank: bool


def parse_line_stream(text: str) -> list[AnnotatedLine]:
    """Parse normalized text into an annotated line stream."""
    lines: list[AnnotatedLine] = []
    current_page: int | None = None
    for index, raw_line in enumerate(text.split("\n")):
        stripped = raw_line.strip()
        marker = _PAGE_MARKER_RE.match(stripped)
        if marker:
            current_page = int(marker.group(1))
            continue
        lines.append(
            AnnotatedLine(
                index=index,
                text=stripped,
                raw_text=raw_line.rstrip("\r"),
                indent=len(raw_line) - len(raw_line.lstrip(" ")),
                page=current_page,
                is_blank=not stripped,
            )
        )
    return lines


def non_blank_lines(lines: list[AnnotatedLine]) -> list[AnnotatedLine]:
    """Return only non-blank lines."""
    return [line for line in lines if not line.is_blank]
