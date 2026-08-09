"""Enumerations for the Knowledge Registry."""

from __future__ import annotations

from enum import StrEnum


class CollectionSlug(StrEnum):
    HR = "hr"
    FINANCE = "finance"
    ENGINEERING = "engineering"
    IT = "it"
    SECURITY = "security"
    LEGAL = "legal"
    MARKETING = "marketing"
    SALES = "sales"
    OPERATIONS = "operations"
    RESEARCH = "research"
    PERSONAL = "personal"
    EXTERNAL = "external"
    SUPPORT = "support"
    ADMIN = "admin"
    UNKNOWN = "unknown"


class KnowledgeHealthStatus(StrEnum):
    VERIFIED = "Verified"
    DRAFT = "Draft"
    ARCHIVED = "Archived"
    SUPERSEDED = "Superseded"
    DUPLICATE = "Duplicate"
    EXTERNAL = "External"
    INCOMPLETE = "Incomplete"
    HEALTHY = "Healthy"
    UNKNOWN = "Unknown"
