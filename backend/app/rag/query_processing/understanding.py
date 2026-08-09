"""Query Understanding — analyze enterprise questions before retrieval.

Tenant-agnostic: uses configurable org aliases and generic enterprise concept
lexicons. Does not hardcode customer-specific document names in code paths;
likely-document hints are generic type labels used only to shape expansions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.query_processing.schemas import ClassificationResult, QueryCategory

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'/&.-]{1,}")
_DOC_ID_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]{2,}){1,3}-\d{2,}\b")
_POLICY_PHRASE_RE = re.compile(
    r"\b([a-z][a-z0-9'/&\- ]{2,40}?)\s+(policy|procedure|standard|handbook|charter|matrix|guide)\b",
    re.I,
)

# Generic enterprise concept detectors → canonical concept key.
# Patterns are intentionally organization-agnostic.
_CONCEPT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mission", (r"\bmission(?:\s+statement)?\b",)),
    ("vision", (r"\bvision\b",)),
    ("core_values", (r"\bcore\s+values?\b", r"\bethical\s+principles?\b", r"\bcompany\s+values?\b")),
    ("metadata", (r"\bmetadata\b", r"\bmeta[- ]?data\b")),
    ("taxonomy", (r"\btaxonom(?:y|ies)\b", r"\bknowledge\s+classificat", r"\bhierarchy\b")),
    ("approval", (r"\bapproval\b", r"\bapprov(?:e|ed|ing)\b", r"\bauthority\s+matrix\b")),
    ("leave", (r"\bleave\b", r"\bpto\b", r"\bencashment\b", r"\bannual\s+leave\b")),
    ("retention", (r"\bretention\b", r"\brecords?\s+retention\b", r"\bretain\b")),
    ("committee", (r"\bcommittee\b", r"\bgovernance\s+structure\b", r"\bboard\s+committee\b")),
    ("business_process", (r"\bbusiness\s+process\b", r"\bprocess\s+classificat", r"\bbp[- ]")),
    ("naming_versioning", (r"\bnaming\b", r"\bversioning\b", r"\bdocument\s+naming\b")),
    ("company_profile", (r"\bcompany\s+profile\b", r"\borgani[sz]ation\s+profile\b", r"\bmaster\s+profile\b")),
)

# Concept → generic document-type hints (not tenant filenames).
_CONCEPT_LIKELY_DOCS: dict[str, tuple[str, ...]] = {
    "mission": ("Company Profile", "Organization Overview"),
    "vision": ("Company Profile", "Organization Overview"),
    "core_values": ("Company Profile", "Code of Conduct"),
    "metadata": ("Enterprise Metadata Standard", "Metadata Standard"),
    "taxonomy": ("Knowledge Taxonomy", "Enterprise Knowledge Taxonomy"),
    "approval": ("Approval Authority Matrix", "Approval Policy", "Delegation of Authority"),
    "leave": ("Leave Policy", "Employee Handbook", "HR Policy"),
    "retention": ("Records Retention Schedule", "Retention Policy"),
    "committee": ("Committee Charter", "Governance Framework"),
    "business_process": ("Business Process Classification Guide", "Process Catalog"),
    "naming_versioning": ("Document Naming Standard", "Versioning Standard"),
    "company_profile": ("Company Profile",),
}

_CONCEPT_DOMAIN: dict[str, str] = {
    "mission": "foundation",
    "vision": "foundation",
    "core_values": "foundation",
    "company_profile": "foundation",
    "metadata": "governance",
    "taxonomy": "governance",
    "committee": "governance",
    "business_process": "governance",
    "naming_versioning": "governance",
    "approval": "controls",
    "leave": "human_resources",
    "retention": "records_management",
}

_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("explain", r"\b(explain|describe|outline)\b"),
    ("define", r"\b(what\s+is|what\s+are|define|definition)\b"),
    ("list", r"\b(list|categories|types|kinds)\b"),
    ("how", r"\b(how\s+(?:is|are|do|does)|process|workflow)\b"),
    ("summarize", r"\b(summarize|summarise|summary)\b"),
)

_INTENT_BY_CONCEPT: dict[str, str] = {
    "mission": "Company Information",
    "vision": "Company Information",
    "core_values": "Company Information",
    "company_profile": "Company Information",
    "metadata": "Metadata Governance",
    "taxonomy": "Knowledge Classification",
    "approval": "Approval Controls",
    "leave": "HR Policy",
    "retention": "Records Management",
    "committee": "Governance",
    "business_process": "Business Process",
    "naming_versioning": "Document Standards",
}

_INTENT_BY_CATEGORY: dict[QueryCategory, str] = {
    QueryCategory.POLICY: "Policy Lookup",
    QueryCategory.PROCEDURE: "Procedure Lookup",
    QueryCategory.DEFINITION: "Definition",
    QueryCategory.LIST: "List / Enumeration",
    QueryCategory.TABLE: "Tabular Lookup",
    QueryCategory.FINANCIAL: "Financial Inquiry",
    QueryCategory.SECURITY: "Security Inquiry",
    QueryCategory.COMPLIANCE: "Compliance Inquiry",
    QueryCategory.ENTITY_LOOKUP: "Entity Lookup",
    QueryCategory.CROSS_DOCUMENT: "Cross-Document Inquiry",
    QueryCategory.GENERAL: "General Inquiry",
}


@dataclass(frozen=True)
class QueryUnderstanding:
    """Structured understanding of a user question for retrieval expansion."""

    intent: str
    entities: tuple[str, ...]
    concepts: tuple[str, ...]
    actions: tuple[str, ...]
    domain: str
    likely_documents: tuple[str, ...]
    confidence: float
    signals: tuple[str, ...] = ()


def _load_org_aliases() -> tuple[str, ...]:
    try:
        from app.config import get_settings

        settings = get_settings()
        aliases: list[str] = []
        display = (getattr(settings, "org_display_name", None) or "").strip()
        if display:
            aliases.append(display)
        for alias in getattr(settings, "org_aliases", None) or []:
            cleaned = str(alias).strip()
            if cleaned and cleaned not in aliases:
                aliases.append(cleaned)
        return tuple(aliases)
    except Exception:  # noqa: BLE001
        return ()


def _detect_concepts(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for concept, patterns in _CONCEPT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                found.append(concept)
                break
    return tuple(found)


def _detect_actions(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for action, pattern in _ACTION_PATTERNS:
        if re.search(pattern, text, re.I):
            found.append(action)
    return tuple(found)


def _detect_entities(text: str, *, org_aliases: tuple[str, ...]) -> tuple[str, ...]:
    entities: list[str] = []
    lowered = text.lower()

    for alias in org_aliases:
        if alias.lower() in lowered and alias not in entities:
            entities.append(alias)

    for match in _DOC_ID_RE.finditer(text):
        doc_id = match.group(0)
        if doc_id not in entities:
            entities.append(doc_id)

    for match in _POLICY_PHRASE_RE.finditer(text):
        phrase = re.sub(r"\s+", " ", match.group(0)).strip()
        if phrase and phrase not in entities and len(phrase) >= 6:
            entities.append(phrase.title() if phrase.islower() else phrase)

    # Light proper-noun spans (2+ Capitalized tokens), excluding question openers.
    for match in re.finditer(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,5})\b", text):
        span = match.group(1).strip()
        if span.lower().startswith(("what ", "how ", "when ", "where ", "who ", "explain ")):
            continue
        if span not in entities and len(span.split()) >= 2:
            entities.append(span)

    return tuple(entities[:12])


def _resolve_intent(
    concepts: tuple[str, ...],
    classification: ClassificationResult | None,
) -> str:
    for concept in concepts:
        if concept in _INTENT_BY_CONCEPT:
            return _INTENT_BY_CONCEPT[concept]
    if classification is not None:
        return _INTENT_BY_CATEGORY.get(classification.category, "General Inquiry")
    return "General Inquiry"


def _resolve_domain(concepts: tuple[str, ...], classification: ClassificationResult | None) -> str:
    for concept in concepts:
        if concept in _CONCEPT_DOMAIN:
            return _CONCEPT_DOMAIN[concept]
    if classification is None:
        return "general"
    mapping = {
        QueryCategory.POLICY: "policy",
        QueryCategory.PROCEDURE: "operations",
        QueryCategory.FINANCIAL: "finance",
        QueryCategory.SECURITY: "security",
        QueryCategory.COMPLIANCE: "compliance",
    }
    return mapping.get(classification.category, "general")


def _likely_documents(concepts: tuple[str, ...], entities: tuple[str, ...]) -> tuple[str, ...]:
    docs: list[str] = []
    for concept in concepts:
        for label in _CONCEPT_LIKELY_DOCS.get(concept, ()):
            if label not in docs:
                docs.append(label)
    for entity in entities:
        lowered = entity.lower()
        if "policy" in lowered or "standard" in lowered or "handbook" in lowered:
            titled = entity if entity[0].isupper() else entity.title()
            if titled not in docs:
                docs.append(titled)
    return tuple(docs[:8])


def understand_query(
    query: str,
    *,
    classification: ClassificationResult | None = None,
    org_aliases: tuple[str, ...] | None = None,
) -> QueryUnderstanding:
    """Analyze *query* into intent / entities / concepts for expansion."""
    text = (query or "").strip()
    if not text:
        return QueryUnderstanding(
            intent="General Inquiry",
            entities=(),
            concepts=(),
            actions=(),
            domain="general",
            likely_documents=(),
            confidence=0.0,
            signals=("empty",),
        )

    aliases = org_aliases if org_aliases is not None else _load_org_aliases()
    concepts = _detect_concepts(text)
    actions = _detect_actions(text)
    entities = _detect_entities(text, org_aliases=aliases)
    intent = _resolve_intent(concepts, classification)
    domain = _resolve_domain(concepts, classification)
    likely_docs = _likely_documents(concepts, entities)

    signals: list[str] = []
    if concepts:
        signals.append("concepts_detected")
    if entities:
        signals.append("entities_detected")
    if actions:
        signals.append("actions_detected")
    if likely_docs:
        signals.append("likely_documents_inferred")

    confidence = 0.45
    if concepts:
        confidence += min(0.35, 0.12 * len(concepts))
    if entities:
        confidence += min(0.15, 0.05 * len(entities))
    if classification is not None:
        confidence = max(confidence, min(0.9, classification.confidence))
    confidence = round(min(0.95, confidence), 4)

    return QueryUnderstanding(
        intent=intent,
        entities=entities,
        concepts=concepts,
        actions=actions,
        domain=domain,
        likely_documents=likely_docs,
        confidence=confidence,
        signals=tuple(signals) or ("none",),
    )
