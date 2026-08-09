"""Canonical enums for the Intelligent Query Planner."""

from __future__ import annotations

from enum import Enum


class QueryIntent(str, Enum):
    DOCUMENT_LOOKUP = "DOCUMENT_LOOKUP"
    METADATA_SEARCH = "METADATA_SEARCH"
    COLLECTION_SEARCH = "COLLECTION_SEARCH"
    DEPARTMENT_SEARCH = "DEPARTMENT_SEARCH"
    ENTITY_SEARCH = "ENTITY_SEARCH"
    TOPIC_SEARCH = "TOPIC_SEARCH"
    KEYWORD_SEARCH = "KEYWORD_SEARCH"
    VERSION_LOOKUP = "VERSION_LOOKUP"
    RELATIONSHIP_QUERY = "RELATIONSHIP_QUERY"
    NAVIGATION = "NAVIGATION"
    COUNT_QUERY = "COUNT_QUERY"
    SUMMARY_REQUEST = "SUMMARY_REQUEST"
    COMPARISON = "COMPARISON"
    POLICY_LOOKUP = "POLICY_LOOKUP"
    UNKNOWN = "UNKNOWN"


class RetrievalStrategy(str, Enum):
    METADATA_ONLY = "Metadata Only"
    METADATA_VERSION = "Metadata + Version"
    DEPARTMENT_TAXONOMY = "Department + Taxonomy"
    RELATIONSHIP_ENTITY = "Relationship + Entity"
    METADATA_RELATIONSHIP_VERSION = "Metadata + Relationship + Version"
    HYBRID = "Hybrid"
    GRAPH_READY = "Graph Ready"
    KEYWORD_TOPIC = "Keyword + Topic"
    COLLECTION_METADATA = "Collection + Metadata"
    FALLBACK_HYBRID = "Fallback Hybrid"


class ExpectedResultType(str, Enum):
    DOCUMENTS = "documents"
    METADATA = "metadata"
    COUNT = "count"
    SUMMARY = "summary"
    RELATIONSHIPS = "relationships"
    COMPARISON = "comparison"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


# Index names aligned with Phase 13.4 KnowledgeIndexManager
INDEX_NAMES = (
    "metadata",
    "collection",
    "department",
    "taxonomy",
    "entity",
    "keyword",
    "topic",
    "tag",
    "relationship",
    "version",
)
