"""Normalize horizontal separators between major sections (Phase 5E)."""

from __future__ import annotations

import re

_MAJOR_HEADING_RE = re.compile(r"^##\s+")
_HR_RE = re.compile(r"^\s*-{3,}\s*$")


def normalize_separators(markdown: str) -> str:
    """
    Ensure `---` appears only between consecutive major (##) sections.

    Never place separators between list items or inside section bodies.
    """
    lines = (markdown or "").splitlines()
    if not lines:
        return ""

    # Drop all existing horizontal rules; we re-insert between ## sections only.
    stripped = [line for line in lines if not _HR_RE.match(line)]

    out: list[str] = []
    i = 0
    while i < len(stripped):
        line = stripped[i]
        if _MAJOR_HEADING_RE.match(line) and out:
            # Find previous non-empty content in out.
            prev_non_empty = next((x for x in reversed(out) if x.strip()), "")
            if prev_non_empty and not _MAJOR_HEADING_RE.match(prev_non_empty):
                # Insert separator before this ## if prior content was a section body.
                # Walk back to see if there was already a prior ## (i.e. this is 2nd+ major section).
                had_prior_major = any(_MAJOR_HEADING_RE.match(x) for x in out)
                if had_prior_major:
                    while out and not out[-1].strip():
                        out.pop()
                    out.append("")
                    out.append("---")
                    out.append("")
        out.append(line)
        i += 1

    return "\n".join(out).strip()
