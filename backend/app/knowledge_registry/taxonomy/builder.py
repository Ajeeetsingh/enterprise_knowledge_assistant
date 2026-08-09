"""Hierarchical taxonomy builder for registered knowledge."""

from __future__ import annotations

from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_registry.types import TaxonomyNode

# collection -> document_type bucket -> optional topic leaf
_TYPE_BUCKETS: dict[str, str] = {
    "policy": "Policies",
    "handbook": "Handbooks",
    "manual": "Procedures",
    "financial report": "Reports",
    "invoice": "Invoices",
    "contract": "Contracts",
    "research paper": "Papers",
    "resume": "Resumes",
    "presentation": "Presentations",
    "unknown": "General",
}

_TOPIC_LEAVES: dict[str, tuple[str, ...]] = {
    "hr": ("Annual Leave", "Leave", "Remote Work", "Performance Review", "Attendance"),
    "finance": ("Budget", "Expense Report", "Revenue", "Expenses"),
    "security": ("Incident Response", "Password Policy", "Multi-Factor Authentication", "Access Control"),
    "it": ("VPN", "Multi-Factor Authentication", "Password Policy"),
}


class TaxonomyBuilder:
    """Build hierarchical taxonomy paths from Knowledge Objects."""

    def build(
        self,
        knowledge: DocumentKnowledge,
        *,
        primary_collection: str,
        canonical_concepts: list[str],
    ) -> tuple[str, list[TaxonomyNode]]:
        collection_name = primary_collection.replace("_", " ").title()
        if primary_collection == "hr":
            collection_name = "HR"
        elif primary_collection == "it":
            collection_name = "IT"

        type_key = knowledge.document_type.strip().lower()
        bucket = _TYPE_BUCKETS.get(type_key, "General")

        leaf = self._resolve_leaf(primary_collection, knowledge, canonical_concepts)
        nodes: list[TaxonomyNode] = [
            TaxonomyNode(path=collection_name, name=collection_name, collection=primary_collection, depth=0),
            TaxonomyNode(
                path=f"{collection_name}/{bucket}",
                name=bucket,
                collection=primary_collection,
                parent_path=collection_name,
                depth=1,
            ),
        ]
        path = f"{collection_name}/{bucket}"
        if leaf:
            path = f"{path}/{leaf}"
            nodes.append(
                TaxonomyNode(
                    path=path,
                    name=leaf,
                    collection=primary_collection,
                    parent_path=f"{collection_name}/{bucket}",
                    depth=2,
                )
            )
        return path, nodes

    def _resolve_leaf(
        self,
        collection: str,
        knowledge: DocumentKnowledge,
        canonical_concepts: list[str],
    ) -> str | None:
        candidates = list(canonical_concepts)
        candidates.extend(knowledge.topics)
        allowed = _TOPIC_LEAVES.get(collection, ())
        haystack = " ".join(
            [knowledge.metadata.filename, knowledge.summary.short, *knowledge.topics, *knowledge.keywords]
        ).lower()
        for concept in candidates:
            if concept in allowed or concept.lower() in haystack:
                # Prefer known leaves for the collection.
                for leaf in allowed:
                    if leaf.lower() == concept.lower() or leaf.lower() in concept.lower() or concept.lower() in leaf.lower():
                        return leaf
        for leaf in allowed:
            if leaf.lower() in haystack:
                return leaf
        return None
