"""Graph node and edge enums."""

from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    KNOWLEDGE_OBJECT = "KnowledgeObject"
    COLLECTION = "Collection"
    DEPARTMENT = "Department"
    ENTITY = "Entity"
    TOPIC = "Topic"
    TAXONOMY = "Taxonomy"
    VERSION_GROUP = "VersionGroup"
    DOCUMENT_TYPE = "DocumentType"


class EdgeType(str, Enum):
    SAME_COLLECTION = "same_collection"
    SAME_DEPARTMENT = "same_department"
    SAME_TAXONOMY = "same_taxonomy"
    MENTIONS = "mentions"
    REFERENCES = "references"
    GOVERNS = "governs"
    EXTENDS = "extends"
    DUPLICATE_OF = "duplicate_of"
    PREVIOUS_VERSION = "previous_version"
    NEXT_VERSION = "next_version"
    RELATED_TO = "related_to"
    BELONGS_TO = "belongs_to"
    CONTAINS_ENTITY = "contains_entity"
    CONTAINS_TOPIC = "contains_topic"
