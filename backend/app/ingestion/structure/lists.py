"""List detection with nested hierarchy."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.line_stream import AnnotatedLine
from app.ingestion.structure.models import ListItem

_BULLET_RE = re.compile(r"^[-*]\s+(?P<text>.+)$")
_ORDERED_RE = re.compile(r"^(?P<marker>\d+|[a-zA-Z])[\.)]\s+(?P<text>.+)$")


@dataclass
class DetectedList:
    """A detected list region in the line stream."""

    start_line_index: int
    end_line_index: int
    ordered: bool
    items: list[ListItem]
    page_start: int | None
    page_end: int | None


def _indent_level(raw_line: str) -> int:
    stripped = raw_line.lstrip(" ")
    indent = len(raw_line) - len(stripped)
    return indent // 2


def _parse_list_line(line: AnnotatedLine) -> tuple[bool, int, str] | None:
    bullet_match = _BULLET_RE.match(line.text)
    if bullet_match:
        return False, line.indent // 2, bullet_match.group("text").strip()

    ordered_match = _ORDERED_RE.match(line.text)
    if ordered_match:
        return True, line.indent // 2, ordered_match.group("text").strip()
    return None


def _append_item(items: list[ListItem], level: int, text: str) -> None:
    if not items:
        items.append(ListItem(text=text, level=level))
        return

    stack: list[list[ListItem]] = [items]
    current_items = items
    current_level = items[-1].level

    while current_level < level and current_items:
        current_items = current_items[-1].children
        current_level += 1
        stack.append(current_items)

    if current_level == level:
        current_items.append(ListItem(text=text, level=level))
        return

    while current_level > level and len(stack) > 1:
        stack.pop()
        current_items = stack[-1]
        current_level -= 1
    current_items.append(ListItem(text=text, level=level))


def detect_lists(
    lines: list[AnnotatedLine],
    settings: StructureExtractionSettings,
    skip_line_indexes: set[int] | None = None,
) -> list[DetectedList]:
    """Detect bullet and numbered lists while preserving hierarchy."""
    skip_line_indexes = skip_line_indexes or set()
    lists: list[DetectedList] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.is_blank or line.index in skip_line_indexes:
            index += 1
            continue

        parsed = _parse_list_line(line)
        if parsed is None:
            index += 1
            continue

        ordered, level, _ = parsed
        if level > settings.max_list_nesting_depth:
            index += 1
            continue

        block_lines = [line]
        items: list[ListItem] = []
        _append_item(items, level, parsed[2])
        scan = index + 1
        while scan < len(lines):
            candidate = lines[scan]
            if candidate.is_blank or candidate.index in skip_line_indexes:
                break
            next_parsed = _parse_list_line(candidate)
            if next_parsed is None:
                break
            next_ordered, next_level, next_text = next_parsed
            if next_ordered != ordered:
                break
            if next_level > settings.max_list_nesting_depth:
                break
            _append_item(items, next_level, next_text)
            block_lines.append(candidate)
            scan += 1

        if items:
            lists.append(
                DetectedList(
                    start_line_index=block_lines[0].index,
                    end_line_index=block_lines[-1].index,
                    ordered=ordered,
                    items=items,
                    page_start=block_lines[0].page,
                    page_end=block_lines[-1].page,
                )
            )
            index = scan
            continue
        index += 1
    return lists
