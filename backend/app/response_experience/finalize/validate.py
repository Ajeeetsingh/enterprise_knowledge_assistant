"""Lightweight markdown structural validation (Phase 5E)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_TABLE_RE = re.compile(r"^\s*\|")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_BQ_RE = re.compile(r"^\s*>")


@dataclass(frozen=True)
class MarkdownValidation:
    ok: bool
    issues: list[str] = field(default_factory=list)
    heading_count: int = 0
    table_count: int = 0
    list_count: int = 0


def validate_markdown(markdown: str) -> MarkdownValidation:
    """Report structural issues without mutating content."""
    issues: list[str] = []
    lines = (markdown or "").splitlines()
    heading_count = 0
    table_count = 0
    list_count = 0
    last_heading_level = 0
    fence_open = False
    unmatched_bold = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            fence_open = not fence_open
            i += 1
            continue
        if fence_open:
            i += 1
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            heading_count += 1
            level = len(heading.group(1))
            if last_heading_level and level > last_heading_level + 1:
                issues.append(f"skipped heading level near '{heading.group(2)[:40]}'")
            last_heading_level = level

        if _LIST_RE.match(line):
            list_count += 1

        if _TABLE_RE.match(line):
            block = []
            while i < len(lines) and _TABLE_RE.match(lines[i]):
                block.append(lines[i])
                i += 1
            table_count += 1
            table_issues = _validate_table(block)
            issues.extend(table_issues)
            continue

        # Unbalanced emphasis heuristic on a line.
        if stripped.count("**") % 2 != 0:
            unmatched_bold += 1

        # Blockquotes: no close marker needed; flag empty quote openers.
        if _BQ_RE.match(line) and not stripped.lstrip(">").strip():
            issues.append("empty blockquote line")

        i += 1

    if fence_open:
        issues.append("unbalanced fenced code block")
    if unmatched_bold:
        issues.append(f"unbalanced bold markers on {unmatched_bold} line(s)")

    return MarkdownValidation(
        ok=not issues,
        issues=issues,
        heading_count=heading_count,
        table_count=table_count,
        list_count=list_count,
    )


def _validate_table(block: list[str]) -> list[str]:
    if len(block) < 2:
        return ["malformed table: fewer than 2 rows"]

    def cols(line: str) -> int:
        raw = line.strip()
        if raw.startswith("|"):
            raw = raw[1:]
        if raw.endswith("|"):
            raw = raw[:-1]
        return len(raw.split("|"))

    widths = [cols(line) for line in block]
    if len(set(widths)) != 1:
        return ["malformed table: inconsistent column counts"]
    sep = block[1].replace("|", "").replace(":", "").replace("-", "").strip()
    if sep:
        return ["malformed table: missing separator row"]
    return []
