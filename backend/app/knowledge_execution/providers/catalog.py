"""Concrete Hybrid Knowledge Index providers."""

from __future__ import annotations

from typing import Any

from app.knowledge_execution.providers.base import IndexProvider
from app.query_planner.models.types import QueryExecutionPlan


def _tokens(plan: QueryExecutionPlan) -> list[str]:
    text = f"{plan.normalized_query} {plan.raw_query}".strip()
    return [part for part in text.replace("/", " ").split() if len(part) > 1]


class MetadataIndexProvider(IndexProvider):
    name = "metadata"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        queries: list[Any] = []
        filters = plan.filters or {}
        constraints = plan.constraints
        mapping = [
            ("filename", constraints.exact_filename or constraints.partial_filename or filters.get("exact_filename") or filters.get("partial_filename")),
            ("document_type", constraints.document_type or filters.get("document_type")),
            ("language", constraints.language or filters.get("language")),
            ("owner", filters.get("owner")),
        ]
        for field, value in mapping:
            if value:
                queries.append({"field": field, "value": value})
        # Fallback: try first significant token as filename fragment via document_type/filename heuristics
        if not queries:
            for token in _tokens(plan)[:3]:
                queries.append({"field": "filename", "value": token})
        return queries


class CollectionIndexProvider(IndexProvider):
    name = "collection"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = []
        if plan.constraints.collection:
            values.append(plan.constraints.collection)
        if plan.filters.get("collection"):
            values.append(str(plan.filters["collection"]))
        for token in _tokens(plan):
            if token.lower() in {"finance", "hr", "security", "it", "legal", "general"}:
                values.append(token)
        return list(dict.fromkeys(values)) or ["General"]


class DepartmentIndexProvider(IndexProvider):
    name = "department"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = []
        if plan.constraints.department:
            values.append(plan.constraints.department)
        for entity in plan.entities:
            if entity.kind == "department":
                values.append(entity.text)
        for token in _tokens(plan):
            if token.upper() in {"HR", "IT"} or token.lower() in {
                "finance",
                "security",
                "legal",
                "operations",
                "engineering",
            }:
                values.append(token.upper() if token.lower() == "hr" else token.capitalize())
        return list(dict.fromkeys(values))


class TaxonomyIndexProvider(IndexProvider):
    name = "taxonomy"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        queries: list[Any] = []
        path = plan.constraints.taxonomy_path or plan.filters.get("taxonomy_path")
        if path:
            queries.append({"mode": "prefix", "value": path})
        # Department/collection as taxonomy prefix
        seed = plan.constraints.department or plan.constraints.collection
        if seed:
            queries.append({"mode": "prefix", "value": seed})
        for token in _tokens(plan)[:2]:
            queries.append({"mode": "prefix", "value": token})
        return queries


class EntityIndexProvider(IndexProvider):
    name = "entity"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = list(plan.constraints.entity_filters or [])
        values.extend(entity.text for entity in plan.entities if entity.kind in {"entity", "document_name"})
        if plan.filters.get("entities"):
            values.extend(plan.filters["entities"])
        return list(dict.fromkeys(values))


class KeywordIndexProvider(IndexProvider):
    name = "keyword"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = [token.lower() for token in _tokens(plan) if token.lower() not in {"the", "a", "an", "of", "in", "for", "to"}]
        return list(dict.fromkeys(values))[:8]


class TopicIndexProvider(IndexProvider):
    name = "topic"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = []
        for entity in plan.entities:
            if entity.kind in {"entity", "document_name"}:
                values.append(entity.text)
        # Phrase-ish topics from normalized query
        if plan.normalized_query:
            values.append(plan.normalized_query)
            values.extend(_tokens(plan)[:4])
        return list(dict.fromkeys(values))


class TagIndexProvider(IndexProvider):
    name = "tag"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        values = []
        if plan.constraints.document_type:
            values.append(plan.constraints.document_type)
        if plan.constraints.department:
            values.append(plan.constraints.department)
        values.extend(_tokens(plan)[:5])
        return list(dict.fromkeys(values))


class RelationshipIndexProvider(IndexProvider):
    name = "relationship"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        queries: list[Any] = []
        for req in plan.relationship_requirements or ["outgoing"]:
            if req.startswith("type:"):
                queries.append({"mode": "type", "value": req.split(":", 1)[1]})
            elif req in {"incoming", "outgoing", "type"}:
                # Prefer entity/knowledge hints from filters if present
                seed = plan.constraints.department or (plan.entities[0].text if plan.entities else "")
                if req == "type":
                    queries.append({"mode": "type", "value": "related_to"})
                else:
                    queries.append({"mode": req, "value": seed})
            else:
                queries.append({"mode": "type", "value": req})
        if not queries:
            queries.append({"mode": "type", "value": "related_to"})
        return queries


class VersionIndexProvider(IndexProvider):
    name = "version"

    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        queries: list[Any] = []
        if plan.constraints.latest or plan.filters.get("latest"):
            # latest needs a group — also collect duplicates/canonical as supporting evidence
            queries.append({"mode": "canonical"})
            queries.append({"mode": "duplicates"})
        if plan.constraints.oldest or plan.filters.get("oldest"):
            queries.append({"mode": "canonical"})
        if plan.constraints.version_label:
            queries.append({"mode": "group", "value": plan.constraints.version_label})
        if not queries:
            queries.append({"mode": "canonical"})
        return queries


PROVIDER_TYPES: dict[str, type[IndexProvider]] = {
    "metadata": MetadataIndexProvider,
    "collection": CollectionIndexProvider,
    "department": DepartmentIndexProvider,
    "taxonomy": TaxonomyIndexProvider,
    "entity": EntityIndexProvider,
    "keyword": KeywordIndexProvider,
    "topic": TopicIndexProvider,
    "tag": TagIndexProvider,
    "relationship": RelationshipIndexProvider,
    "version": VersionIndexProvider,
}


def build_providers(manager) -> dict[str, IndexProvider]:
    return {name: cls(manager) for name, cls in PROVIDER_TYPES.items()}
