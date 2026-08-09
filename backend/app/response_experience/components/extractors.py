"""Deterministic extractors for adaptive components (no invention)."""

from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_NUMBERED_RE = re.compile(r"^\s*(?:\d+[\.)]|[-*•])\s+(.+)$", re.M)
_ARROW_STEP_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9 /_-]{2,40}?)\s*(?:→|->|↓|then)\s*",
    re.I,
)
_ROLE_LINE_RE = re.compile(
    r"^(?:[-*•]\s*)?"
    r"([A-Z][A-Za-z0-9 /&-]{2,40}?)"
    r"\s*(?::|—|-|–)\s+"
    r"(.+)$",
    re.M,
)
_NOTE_RE = re.compile(
    r"(?i)\b(important|note|exception|must|shall|warning|constraint)\b"
)
_COMPARE_PAIR_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9 /-]{2,30})\s+(?:vs\.?|versus|compared to|and)\s+"
    r"([A-Z][A-Za-z0-9 /-]{2,30})\b"
)
_LEVEL_RE = re.compile(
    r"^(?:[-*]\s*)?(L[1-4]|Level\s*[1-4])\s*[:.\-–—]?\s*(.+)$",
    re.I | re.M,
)
_DECISION_MARKERS = (
    ("situation", re.compile(r"(?i)\b(situation|when|if|scenario)\b[:\s-]*(.+)")),
    (
        "committee",
        re.compile(
            r"(?i)\b(committee|authority|approver|approval (?:path|matrix|rules?))\b[:\s-]*(.+)"
        ),
    ),
    ("escalation", re.compile(r"(?i)\b(escalat\w*|board)\b[:\s-]*(.+)")),
)


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return []
    parts = _SENTENCE_RE.split(cleaned)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def extract_list_items(text: str) -> list[str]:
    items = [match.group(1).strip() for match in _NUMBERED_RE.finditer(text or "")]
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen or len(item) < 2:
            continue
        seen.add(key)
        out.append(item)
    return out


def extract_step_labels(text: str) -> list[str]:
    """Pull workflow step labels from numbered lists or arrow language."""
    items = extract_list_items(text)
    if items:
        # Prefer short labels (first clause).
        labels: list[str] = []
        for item in items:
            label = re.split(r"[:.\-–—]", item, maxsplit=1)[0].strip()
            if 2 <= len(label) <= 48:
                labels.append(label)
            else:
                labels.append(item[:48].strip())
        return labels

    # Fallback: "A then B then C" style.
    lowered = text or ""
    then_parts = re.split(r"\bthen\b", lowered, flags=re.I)
    if len(then_parts) >= 3:
        labels = []
        for part in then_parts:
            token = re.sub(r"[^A-Za-z0-9 /_-]+", " ", part).strip()
            token = " ".join(token.split()[:4])
            if len(token) >= 3:
                labels.append(token.title() if token.islower() else token)
        if len(labels) >= 3:
            return labels[:8]
    return []


def extract_note_sentences(text: str) -> list[str]:
    return [sentence for sentence in split_sentences(text) if _NOTE_RE.search(sentence)]


def extract_role_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for match in _ROLE_LINE_RE.finditer(text or ""):
        role = match.group(1).strip()
        responsibility = match.group(2).strip()
        if len(role) < 2 or len(responsibility) < 8:
            continue
        # Avoid capturing ordinary sentences with a colon mid-thought.
        if len(role.split()) > 6:
            continue
        rows.append((role, responsibility))
    return rows[:8]


def extract_comparison_entities(text: str) -> tuple[str, str] | None:
    match = _COMPARE_PAIR_RE.search(text or "")
    if not match:
        return None
    left, right = match.group(1).strip(), match.group(2).strip()
    if left.lower() == right.lower():
        return None
    return left, right


def extract_level_rows(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for match in _LEVEL_RE.finditer(text or ""):
        raw = match.group(1)
        digits = re.search(r"[1-4]", raw)
        if not digits:
            continue
        label = match.group(2).strip()
        if label:
            rows.append((int(digits.group(0)), label))
    return rows


def extract_decision_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, pattern in _DECISION_MARKERS:
        match = pattern.search(text or "")
        if match:
            value = match.group(match.lastindex or 1).strip()
            if len(value) >= 3:
                fields[key] = value[:180]
    # Soft fallbacks from free text for committee / approval questions.
    if "committee" not in fields:
        committee = re.search(
            r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4}\s+Committee)\b",
            text or "",
        )
        if committee:
            fields["committee"] = committee.group(1)
        else:
            authority = re.search(
                r"([^.!?]{0,80}\b(?:approval authority|delegated authority|authority matrix)\b[^.!?]*[.!?])",
                text or "",
                re.I,
            )
            if authority:
                fields["committee"] = authority.group(1).strip()
    if "escalation" not in fields:
        esc = re.search(
            r"\b(escalat(?:e|es|ion)[^.?!]*[.?!])",
            text or "",
            re.I,
        )
        if esc:
            fields["escalation"] = esc.group(1).strip()
        else:
            material = re.search(
                r"([^.!?]{0,100}\b(?:material changes?|escalate|thresholds?)\b[^.!?]*[.!?])",
                text or "",
                re.I,
            )
            if material:
                fields["escalation"] = material.group(1).strip()
    if "situation" not in fields:
        sentences = split_sentences(text)
        if sentences:
            fields["situation"] = sentences[0]
    return fields


def pretty_document_name(source: str) -> str:
    name = (source or "").strip()
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    name = re.sub(r"^\d+_", "", name)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else source
