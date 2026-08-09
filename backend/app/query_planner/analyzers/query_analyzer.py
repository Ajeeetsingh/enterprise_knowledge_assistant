"""Query analysis — entities, departments, collections, versions, filters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.query_planner.models.types import ExtractedEntity
from app.query_planner.parser.normalizer import NormalizationResult

_DEPARTMENTS = ("HR", "Finance", "Security", "IT", "Legal", "Operations", "Engineering")
_COLLECTIONS = ("Finance", "HR", "Security", "IT", "Legal", "General")
_DOC_TYPES = ("Policy", "Handbook", "Manual", "Report", "Financial Report", "Guide")
_ENTITY_LEXICON = (
    "MFA",
    "VPN",
    "Employee",
    "Company",
    "Budget",
    "Incident",
    "Password",
    "Leave",
    "Policy",
)


@dataclass
class QueryAnalysis:
    entities: list[ExtractedEntity] = field(default_factory=list)
    document_names: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    taxonomy_paths: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)
    requested_output: str | None = None
    topics: list[str] = field(default_factory=list)


class QueryAnalyzer:
    def analyze(self, normalization: NormalizationResult) -> QueryAnalysis:
        text = normalization.normalized
        lower = text.lower()
        analysis = QueryAnalysis()

        for phrase in normalization.quoted_phrases:
            analysis.document_names.append(phrase)
            analysis.entities.append(
                ExtractedEntity(text=phrase, kind="document_name", confidence=0.9)
            )

        for dept in _DEPARTMENTS:
            if re.search(rf"\b{re.escape(dept)}\b", text, re.IGNORECASE):
                analysis.departments.append(dept)
                analysis.entities.append(
                    ExtractedEntity(text=dept, kind="department", confidence=0.85)
                )

        for collection in _COLLECTIONS:
            if re.search(rf"\b{re.escape(collection)}\b", lower, re.IGNORECASE):
                if collection not in analysis.collections:
                    analysis.collections.append(collection)

        for doc_type in _DOC_TYPES:
            if doc_type.lower() in lower:
                analysis.filters["document_type"] = doc_type

        for entity in _ENTITY_LEXICON:
            if re.search(rf"\b{re.escape(entity)}\b", text, re.IGNORECASE):
                analysis.entities.append(
                    ExtractedEntity(text=entity, kind="entity", confidence=0.75)
                )

        # Taxonomy-like path fragments
        path_match = re.search(r"\b([A-Za-z]+/[A-Za-z0-9_ /-]+)\b", text)
        if path_match:
            analysis.taxonomy_paths.append(path_match.group(1).strip())

        if "leave" in lower or "annual leave" in lower:
            analysis.topics.append("Leave Policy")
        if "password" in lower:
            analysis.topics.append("Password Policy")
        if "remote" in lower or "wfh" in lower:
            analysis.topics.append("Remote Work")
        if "incident" in lower:
            analysis.topics.append("Incident Response")

        version_matches = re.findall(r"\b(v\d+|final|latest|oldest|draft)\b", lower)
        analysis.versions.extend(version_matches)

        date_matches = re.findall(r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|20\d{2})\b", text)
        analysis.dates.extend(date_matches)

        if re.search(r"\bsummar", lower):
            analysis.requested_output = "summary"
        elif re.search(r"\bhow many\b|\bcount\b", lower):
            analysis.requested_output = "count"
        elif re.search(r"\bcompare\b|\bversus\b|\bvs\b", lower):
            analysis.requested_output = "comparison"
        elif re.search(r"\brelated\b|\brelationship\b", lower):
            analysis.requested_output = "relationships"
        else:
            analysis.requested_output = "documents"

        # Filename hints
        file_match = re.search(r"([\w-]+\.(?:pdf|docx?|txt|md))", lower)
        if file_match:
            analysis.document_names.append(file_match.group(1))
            analysis.filters["partial_filename"] = file_match.group(1)

        return analysis
