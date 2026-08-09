"""Context-aware bold emphasis for scannable enterprise terms (Phase 5D)."""

from __future__ import annotations

import re

from app.response_experience.polish.style_guide import MAX_BOLD_SPANS_PER_SECTION

# Patterns that benefit scanning — applied only to non-heading, non-table lines.
_EMPHASIS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b("
        r"[A-Z][A-Za-z0-9 /&-]{2,60}?\s(?:Policy|Standard|Charter|Matrix|Guide|Framework)"
        r")\b"
    ),
    re.compile(
        r"\b("
        r"[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,5}\s+Committee"
        r")\b"
    ),
    re.compile(r"\b((?:DOC|ANB|EKM)[-_A-Z0-9]{3,})\b"),
    re.compile(r"\b(High|Medium|Low)\s+Risk\b", re.I),
    re.compile(
        r"\b("
        r"(?:must|shall)\s+[a-z]+(?:\s+[a-z]+){0,8}"
        r")\b",
        re.I,
    ),
    re.compile(
        r"\b("
        r"(?:review cycle|owner|retention period|approval limit)"
        r"\s*[:=]?\s*[A-Za-z0-9 /-]{2,40}"
        r")\b",
        re.I,
    ),
    re.compile(
        r"\b("
        r"(?:Administrative|Business|Technical|Compliance)\s+Metadata"
        r")\b"
    ),
    re.compile(r"\b(L[1-4])\b"),
)

_ALREADY_BOLD_RE = re.compile(r"\*\*[^*]+\*\*")
_CODE_RE = re.compile(r"`[^`]+`")


def _protected_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in (_ALREADY_BOLD_RE, _CODE_RE):
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))
    return spans


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    for left, right in spans:
        if start < right and end > left:
            return True
    return False


def emphasize_line(line: str) -> str:
    """Bold scannable enterprise terms on a single prose line."""
    stripped = line.lstrip()
    if not stripped:
        return line
    if stripped.startswith(("#", "|", ">", "---", "✔", "•", "- ", "* ", "1.", "└", "↓")):
        return line
    if re.match(r"^\d+\.\s", stripped):
        return line

    protected = _protected_spans(line)
    replacements: list[tuple[int, int, str]] = []
    for pattern in _EMPHASIS_PATTERNS:
        for match in pattern.finditer(line):
            start, end = match.start(1), match.end(1)
            if _overlaps(start, end, protected):
                continue
            phrase = match.group(1)
            if phrase.startswith("**"):
                continue
            replacements.append((start, end, f"**{phrase}**"))
            protected.append((start, end))
            if len(replacements) >= MAX_BOLD_SPANS_PER_SECTION:
                break
        if len(replacements) >= MAX_BOLD_SPANS_PER_SECTION:
            break

    if not replacements:
        return line
    replacements.sort(key=lambda item: item[0], reverse=True)
    out = line
    for start, end, repl in replacements:
        out = out[:start] + repl + out[end:]
    return out


def emphasize_markdown(markdown: str) -> str:
    return "\n".join(emphasize_line(line) for line in (markdown or "").splitlines())
