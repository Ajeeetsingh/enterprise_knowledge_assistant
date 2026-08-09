"""Deterministic document-topic ownership for synthesis (Phase 4F)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Topic key → patterns that identify owning source filenames.
_OWNER_RULES: tuple[tuple[str, re.Pattern[str], tuple[str, ...]], ...] = (
    (
        "company_profile",
        re.compile(r"\b(mission|vision|core values?|company profile|who we are)\b", re.I),
        ("company_profile", "profile", "company overview"),
    ),
    (
        "metadata",
        re.compile(r"\bmetadata\b", re.I),
        ("metadata",),
    ),
    (
        "taxonomy",
        re.compile(r"\b(taxonomy|hierarchy|enterprise search)\b", re.I),
        ("taxonomy", "knowledge_taxonomy"),
    ),
    (
        "naming",
        re.compile(r"\b(naming|versioning|document id|filename)\b", re.I),
        ("naming", "versioning"),
    ),
    (
        "retention",
        re.compile(r"\b(retention|records retention|archival)\b", re.I),
        ("retention", "records"),
    ),
    (
        "approval",
        re.compile(r"\b(approval|authority matrix|who (?:should|must) approve)\b", re.I),
        ("approval", "authority_matrix"),
    ),
    (
        "committee",
        re.compile(r"\b(committee|charter|governance body)\b", re.I),
        ("committee", "charter"),
    ),
    (
        "business_process",
        re.compile(r"\b(business process|process classification|l3 process)\b", re.I),
        ("business_process", "process_classification", "process_guide"),
    ),
)

# Canonical governance / lifecycle concept flow for multi-document synthesis.
CONCEPT_FLOW: tuple[str, ...] = (
    "Metadata",
    "Taxonomy",
    "Naming",
    "Classification",
    "Approval",
    "Publication",
    "Retention",
    "Committee",
    "Governance",
)

_CONCEPT_MATCHERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Metadata", re.compile(r"\bmetadata\b", re.I)),
    ("Taxonomy", re.compile(r"\b(taxonomy|hierarchy)\b", re.I)),
    ("Naming", re.compile(r"\b(naming|version|filename|document id)\b", re.I)),
    ("Classification", re.compile(r"\b(classif|business process|l3)\b", re.I)),
    ("Approval", re.compile(r"\bapprov", re.I)),
    ("Publication", re.compile(r"\b(publish|publication|release)\b", re.I)),
    ("Retention", re.compile(r"\b(retention|retain|archiv)\b", re.I)),
    ("Committee", re.compile(r"\bcommittee\b", re.I)),
    ("Governance", re.compile(r"\b(governance|oversight|journey)\b", re.I)),
    ("Mission", re.compile(r"\bmission\b", re.I)),
    ("Vision", re.compile(r"\bvision\b", re.I)),
    ("Core Values", re.compile(r"\b(core values?|values)\b", re.I)),
    ("Knowledge Management", re.compile(r"\b(knowledge management|ekm)\b", re.I)),
)


@dataclass(frozen=True)
class TopicOwnership:
    topic_key: str
    source_hints: tuple[str, ...]


def detect_question_topics(question: str) -> list[TopicOwnership]:
    text = question or ""
    found: list[TopicOwnership] = []
    for key, pattern, hints in _OWNER_RULES:
        if pattern.search(text):
            found.append(TopicOwnership(topic_key=key, source_hints=hints))
    return found


def source_matches_hints(source: str, hints: tuple[str, ...]) -> bool:
    normalized = (source or "").lower().replace("-", "_").replace(" ", "_")
    return any(hint.replace(" ", "_") in normalized for hint in hints)


def infer_concept_label(label: str, source: str, texts: list[str]) -> str:
    """Map an evidence group to a human concept section title."""
    # Prefer the organizer label / section title — avoids mis-tagging from body text
    # (e.g. Retention evidence mentioning "publication").
    label_blob = f"{label or ''} {source or ''}"
    for concept, pattern in _CONCEPT_MATCHERS:
        if pattern.search(label_blob):
            return concept
    body = " ".join(texts[:2])
    for concept, pattern in _CONCEPT_MATCHERS:
        if pattern.search(body):
            return concept
    cleaned = (label or "Evidence").strip()
    return cleaned or "Evidence"


def concept_flow_rank(concept: str) -> int:
    try:
        return CONCEPT_FLOW.index(concept)
    except ValueError:
        return 100
