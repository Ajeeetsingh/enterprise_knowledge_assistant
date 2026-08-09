"""Standardized markdown callouts from natural guidance language (Phase 5D)."""

from __future__ import annotations

import re

_IMPORTANT_RE = re.compile(
    r"^(?P<prefix>\s*(?:[-*•✔]\s+)?)(?P<body>(?:.*?)\b(?:must|shall|mandatory|required before|prohibited)\b.*)$",
    re.I,
)
_NOTE_RE = re.compile(
    r"^(?P<prefix>\s*(?:[-*•✔]\s+)?)(?P<body>(?:note|important)[:\s-]+.+)$",
    re.I,
)
_ALREADY_CALLOUT_RE = re.compile(r"^\s*>")


def _to_callout(kind: str, body: str) -> str:
    cleaned = body.strip()
    cleaned = re.sub(r"^(?:note|important)\s*[:\-–—]\s*", "", cleaned, flags=re.I)
    return f"> **{kind}**\n> {cleaned}"


def apply_callouts(markdown: str) -> str:
    """Convert naturally important lines into callouts; never invent warnings."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _ALREADY_CALLOUT_RE.match(line) or line.startswith("#") or line.startswith("|"):
            out.append(line)
            index += 1
            continue

        note_match = _NOTE_RE.match(line.strip())
        if note_match and len(note_match.group("body")) >= 24:
            out.append(_to_callout("Note", note_match.group("body")))
            index += 1
            continue

        important_match = _IMPORTANT_RE.match(line.strip())
        if important_match and len(important_match.group("body")) >= 28:
            # Prefer Important for mandatory language; skip pure checklist chrome.
            body = important_match.group("body")
            if not body.startswith("✔"):
                out.append(_to_callout("Important", body))
                index += 1
                continue

        out.append(line)
        index += 1
    return "\n".join(out)
