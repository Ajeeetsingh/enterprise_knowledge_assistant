"""Extract expected answer concepts from the question (deterministic)."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

# Ordered concept extractors: (concept_label, patterns that must all/any match)
_CONCEPT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Mission", re.compile(r"\bmission\b", re.I)),
    ("Vision", re.compile(r"\bvision\b", re.I)),
    ("Core Values", re.compile(r"\bcore values?\b|\bvalues\b", re.I)),
    ("Metadata Categories", re.compile(r"\bmetadata\b.*\bcategor|\bcategories of metadata\b", re.I)),
    ("Taxonomy Hierarchy", re.compile(r"\btaxonomy\b|\bhierarchy\b", re.I)),
    ("Enterprise Search", re.compile(r"\benterprise search\b|\bsupports? .*search\b", re.I)),
    ("Document Identifiers", re.compile(r"\bdocument id|\bidentifiers?\b", re.I)),
    ("Filenames", re.compile(r"\bfilenames?\b|\bfile names?\b", re.I)),
    ("Versioning", re.compile(r"\bversioning\b|\bversions?\b", re.I)),
    ("Governance Journey", re.compile(r"\bgovernance journey\b|\bjourney\b", re.I)),
    ("Committee", re.compile(r"\bcommittee\b", re.I)),
    ("Approval", re.compile(r"\bapprov", re.I)),
    ("Lifecycle", re.compile(r"\blifecycle\b|\blife cycle\b", re.I)),
    ("Retention", re.compile(r"\bretention\b", re.I)),
    ("Business Process", re.compile(r"\bbusiness process\b|\bclassification\b", re.I)),
    ("Naming", re.compile(r"\bnaming\b", re.I)),
    ("Knowledge Management", re.compile(r"\bknowledge management\b|\bhead of\b", re.I)),
)


def extract_question_concepts(question: str) -> list[str]:
    """Return expected concepts mentioned or implied by the question."""
    text = (question or "").strip()
    if not text:
        return []
    found: list[str] = []
    for label, pattern in _CONCEPT_RULES:
        if pattern.search(text) and label not in found:
            found.append(label)
    # "values" alone after mission/vision should be Core Values; avoid double-count.
    if "Core Values" in found and "Mission" not in found and "Vision" not in found:
        # keep Core Values for value-only questions
        pass
    return found


def concept_aliases(concept: str) -> tuple[str, ...]:
    """Alias strings used when scanning the answer/evidence."""
    mapping = {
        "Mission": ("mission",),
        "Vision": ("vision",),
        "Core Values": ("core values", "core value", "values"),
        "Metadata Categories": ("metadata", "categor"),
        "Taxonomy Hierarchy": ("taxonomy", "hierarchy", "l1", "l2", "level"),
        "Enterprise Search": ("search", "enterprise search"),
        "Document Identifiers": ("document id", "identifier"),
        "Filenames": ("filename", "file name", "naming"),
        "Versioning": ("version", "versioning"),
        "Governance Journey": ("journey", "governance", "lifecycle", "creation", "approval"),
        "Committee": ("committee",),
        "Approval": ("approv", "authority"),
        "Lifecycle": ("lifecycle", "life cycle", "creation", "retention", "publication"),
        "Retention": ("retention", "retain"),
        "Business Process": ("business process", "process classification", "l3"),
        "Naming": ("naming", "filename"),
        "Knowledge Management": ("knowledge management", "ekmo"),
    }
    return mapping.get(concept, (concept.lower(),))


def contains_concept(text: str, concept: str) -> bool:
    lowered = (text or "").lower()
    return any(alias in lowered for alias in concept_aliases(concept))


def tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))
