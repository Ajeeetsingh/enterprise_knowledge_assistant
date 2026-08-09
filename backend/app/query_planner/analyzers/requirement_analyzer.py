"""Determine which Hybrid Knowledge Indexes a plan requires."""

from __future__ import annotations

from app.query_planner.analyzers.query_analyzer import QueryAnalysis
from app.query_planner.enums import QueryIntent
from app.query_planner.models.types import IntentCandidate, QueryConstraints


# Intent → default required indexes
_INTENT_INDEXES: dict[str, tuple[str, ...]] = {
    QueryIntent.DOCUMENT_LOOKUP.value: ("metadata", "keyword"),
    QueryIntent.METADATA_SEARCH.value: ("metadata",),
    QueryIntent.COLLECTION_SEARCH.value: ("collection", "metadata"),
    QueryIntent.DEPARTMENT_SEARCH.value: ("department", "taxonomy"),
    QueryIntent.ENTITY_SEARCH.value: ("entity", "keyword"),
    QueryIntent.TOPIC_SEARCH.value: ("topic", "keyword"),
    QueryIntent.KEYWORD_SEARCH.value: ("keyword", "topic"),
    QueryIntent.VERSION_LOOKUP.value: ("version", "metadata", "taxonomy"),
    QueryIntent.RELATIONSHIP_QUERY.value: ("relationship", "entity", "metadata"),
    QueryIntent.NAVIGATION.value: ("taxonomy", "collection"),
    QueryIntent.COUNT_QUERY.value: ("metadata", "collection"),
    QueryIntent.SUMMARY_REQUEST.value: ("metadata", "topic", "keyword"),
    QueryIntent.COMPARISON.value: ("metadata", "relationship", "version"),
    QueryIntent.POLICY_LOOKUP.value: ("taxonomy", "department", "keyword", "metadata"),
    QueryIntent.UNKNOWN.value: ("keyword", "metadata"),
}


class KnowledgeRequirementAnalyzer:
    def required_indexes(
        self,
        intents: list[IntentCandidate],
        constraints: QueryConstraints,
        analysis: QueryAnalysis,
    ) -> list[str]:
        needed: list[str] = []
        primary = intents[0].intent if intents else QueryIntent.UNKNOWN.value
        needed.extend(_INTENT_INDEXES.get(primary, ("keyword", "metadata")))

        if constraints.latest or constraints.oldest or constraints.version_label:
            needed.extend(["version", "metadata"])
        if constraints.department:
            needed.append("department")
        if constraints.collection:
            needed.append("collection")
        if constraints.taxonomy_path or analysis.taxonomy_paths:
            needed.append("taxonomy")
        if constraints.entity_filters or any(e.kind == "entity" for e in analysis.entities):
            needed.append("entity")
        if constraints.exact_filename or constraints.partial_filename or constraints.document_type:
            needed.append("metadata")
        if analysis.topics:
            needed.append("topic")

        # Deduplicate preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for name in needed:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    def relationship_requirements(
        self,
        intents: list[IntentCandidate],
    ) -> list[str]:
        primary = intents[0].intent if intents else QueryIntent.UNKNOWN.value
        if primary in {
            QueryIntent.RELATIONSHIP_QUERY.value,
            QueryIntent.COMPARISON.value,
        }:
            return ["incoming", "outgoing", "type"]
        if primary == QueryIntent.VERSION_LOOKUP.value:
            return ["type:duplicate_of", "type:supersedes"]
        return []
