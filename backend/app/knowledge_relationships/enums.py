"""Extensible relationship type catalog."""

from __future__ import annotations

from enum import StrEnum


class RelationshipType(StrEnum):
    # Structural
    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"

    # Semantic
    REFERENCES = "references"
    RELATED_TO = "related_to"
    EXPLAINS = "explains"
    EXTENDS = "extends"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"

    # Organizational
    SAME_DEPARTMENT = "same_department"
    SAME_COLLECTION = "same_collection"
    SAME_TAXONOMY = "same_taxonomy"

    # Versioning
    PREVIOUS_VERSION = "previous_version"
    NEXT_VERSION = "next_version"
    SUPERSEDES = "supersedes"
    DUPLICATE_OF = "duplicate_of"

    # Cross-domain
    SUPPORTS = "supports"
    REQUIRES = "requires"
    GOVERNS = "governs"
    MENTIONS = "mentions"


class RelationshipStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class EvidenceSource(StrEnum):
    TAXONOMY = "taxonomy"
    COLLECTION = "collection"
    ALIAS = "alias"
    CANONICAL_CONCEPT = "canonical_concept"
    VERSION_GROUP = "version_group"
    DUPLICATE_SIGNAL = "duplicate_signal"
    DOCUMENT_TYPE = "document_type"
    # Reserved for future LLM-generated relationships
    LLM = "llm"


class ConfidenceKind(StrEnum):
    HEURISTIC_ESTIMATE = "heuristic_estimate"
    MODEL = "model"
