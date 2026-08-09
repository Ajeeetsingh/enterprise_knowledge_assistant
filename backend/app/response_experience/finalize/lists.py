"""Standardize list markers and indentation (Phase 5E)."""

from __future__ import annotations

import re

_BULLET_RE = re.compile(r"^(\s*)([-*+•▪◦]|✔|✓)\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_CHECK_RE = re.compile(r"^(\s*)(?:[-*+]\s+)?\[([ xX])\]\s+(.*)$")


def normalize_lists(markdown: str) -> str:
    """
    Standardize bullets to `- `, numbered to `1. `, checklists to `- [ ]` / `- [x]`.

    Nested indentation is normalized to multiples of 2 spaces.
    """
    out: list[str] = []
    for line in (markdown or "").splitlines():
        check = _CHECK_RE.match(line)
        if check:
            indent = _normalize_indent(check.group(1))
            mark = "x" if check.group(2).lower() == "x" else " "
            out.append(f"{indent}- [{mark}] {check.group(3).rstrip()}")
            continue

        numbered = _NUMBERED_RE.match(line)
        if numbered:
            indent = _normalize_indent(numbered.group(1))
            out.append(f"{indent}{numbered.group(2)}. {numbered.group(3).rstrip()}")
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            indent = _normalize_indent(bullet.group(1))
            marker = bullet.group(2)
            body = bullet.group(3).rstrip()
            if marker in {"✔", "✓"}:
                out.append(f"{indent}- ✔ {body}")
            else:
                out.append(f"{indent}- {body}")
            continue

        out.append(line)
    return "\n".join(out)


def _normalize_indent(raw: str) -> str:
    spaces = len(raw.expandtabs(2))
    level = max(0, spaces // 2)
    # Cap extreme nesting that usually indicates accidental tabs/spaces.
    level = min(level, 4)
    return "  " * level
