"""Edge-case presentation polish without content invention (Phase 5E)."""

from __future__ import annotations

import re

_REFUSAL_HINTS = (
    "cannot answer",
    "can't answer",
    "not available in",
    "no supporting evidence",
    "does not contain",
    "i don't have",
    "unable to confirm",
    "not found in the",
)
_UNKNOWN_HINTS = (
    "unknown",
    "not specified",
    "insufficient evidence",
    "cannot determine",
)
# Bold that split a hyphenated identifier: **DOC-DOMAIN-NAME-**vMAJOR
_MID_TOKEN_BOLD_RE = re.compile(
    r"\*\*([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-)\*\*([A-Za-z0-9])"
)


def polish_edge_cases(markdown: str) -> str:
    """
    Keep short / refusal / partial answers visually clean.

    - Collapse orphan separators
    - Avoid trailing ---
    - Repair mid-token bold artifacts that break identifiers
    """
    text = (markdown or "").strip()
    if not text:
        return ""

    text = _MID_TOKEN_BOLD_RE.sub(r"\1\2", text)

    lines = text.splitlines()
    # Drop leading/trailing horizontal rules.
    while lines and lines[0].strip() == "---":
        lines.pop(0)
    while lines and lines[-1].strip() == "---":
        lines.pop()

    # Remove --- that sit with blank neighbors only (orphan separators).
    cleaned: list[str] = []
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            prev_empty = not cleaned or cleaned[-1].strip() == ""
            next_empty = idx + 1 >= len(lines) or lines[idx + 1].strip() == ""
            # Keep separators between section bodies; drop stacked rules.
            if cleaned and cleaned[-1].strip() == "---":
                continue
            if prev_empty and next_empty and len(cleaned) <= 1:
                continue
        cleaned.append(line)

    text = "\n".join(cleaned).strip()

    # Very short answers: ensure they are not wrapped in empty chrome.
    non_empty = [line for line in text.splitlines() if line.strip()]
    if len(non_empty) <= 3 and not any(line.startswith("#") for line in non_empty):
        return text + "\n"

    lower = text.lower()
    is_refusal = any(hint in lower for hint in _REFUSAL_HINTS)
    is_unknown = any(hint in lower for hint in _UNKNOWN_HINTS)
    if is_refusal or is_unknown:
        # Ensure no decorative separators inside short refusal bodies.
        if len(non_empty) < 12:
            text = "\n".join(
                line for line in text.splitlines() if line.strip() != "---"
            ).strip()

    return text + "\n"
