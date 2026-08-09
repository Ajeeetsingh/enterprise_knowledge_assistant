"""Global spacing consistency for enterprise markdown (Phase 5E)."""

from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^#{1,3}\s+")
_HR_RE = re.compile(r"^\s*-{3,}\s*$")
_TABLE_RE = re.compile(r"^\s*\|")
_FOOTER_RE = re.compile(r"^##\s+(Sources|Related Documents)\s*$", re.I)


def normalize_spacing(markdown: str) -> str:
    """
    Enforce:
    - single blank line after headings
    - single blank line around tables and --- separators
    - single blank line before Sources / Related Documents
    - no accidental double blank lines
    """
    raw_lines = [line.rstrip() for line in (markdown or "").splitlines()]
    lines: list[str] = []
    for line in raw_lines:
        if not line.strip():
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(line)

    out: list[str] = []
    for idx, line in enumerate(lines):
        prev = out[-1] if out else None
        nxt = lines[idx + 1] if idx + 1 < len(lines) else None

        lead_blank = False
        if prev is not None and prev != "":
            if _HR_RE.match(line) or _FOOTER_RE.match(line):
                lead_blank = True
            elif _TABLE_RE.match(line) and not _TABLE_RE.match(prev):
                lead_blank = True
            elif _HEADING_RE.match(line):
                lead_blank = True
        if lead_blank:
            out.append("")

        out.append(line)

        if nxt is None or nxt == "":
            continue
        after_heading = bool(_HEADING_RE.match(line))
        after_hr = bool(_HR_RE.match(line))
        end_table = bool(_TABLE_RE.match(line)) and not _TABLE_RE.match(nxt)
        if after_heading or after_hr or end_table:
            out.append("")

    final: list[str] = []
    for line in out:
        if line == "" and final and final[-1] == "":
            continue
        final.append(line)

    return "\n".join(final).strip() + "\n"
