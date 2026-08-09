"""Aggregate relationship statistics for the Validation Console."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.types import KnowledgeRelationshipRecord, RelationshipStatistics


def build_relationship_statistics(
    relationships: list[KnowledgeRelationshipRecord],
    entries: list[RegistryEntry],
) -> RelationshipStatistics:
    type_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    buckets: Counter[str] = Counter()
    degree: dict[str, int] = defaultdict(int)
    confidences: list[float] = []

    for rel in relationships:
        type_counts[rel.relationship_type] += 1
        evidence_counts[rel.evidence_source] += 1
        confidences.append(rel.confidence)
        degree[rel.source_knowledge_id] += 1
        degree[rel.target_knowledge_id] += 1
        if rel.confidence < 0.6:
            buckets["0.0-0.6"] += 1
        elif rel.confidence < 0.75:
            buckets["0.6-0.75"] += 1
        elif rel.confidence < 0.9:
            buckets["0.75-0.9"] += 1
        else:
            buckets["0.9-1.0"] += 1

    connected_ids = set(degree)
    filename_by_id = {entry.knowledge_id: entry.filename for entry in entries}
    without = [
        entry.filename
        for entry in entries
        if entry.knowledge_id not in connected_ids
    ]
    top = sorted(
        (
            {
                "knowledge_id": kid,
                "filename": filename_by_id.get(kid, kid),
                "degree": count,
            }
            for kid, count in degree.items()
        ),
        key=lambda item: item["degree"],
        reverse=True,
    )[:10]

    total_docs = len(entries) or 1
    return RelationshipStatistics(
        relationship_count=len(relationships),
        type_counts=dict(type_counts),
        evidence_source_counts=dict(evidence_counts),
        confidence_buckets=dict(buckets),
        documents_with_relationships=len(connected_ids),
        documents_without_relationships=without,
        coverage=round(len(connected_ids) / total_docs, 3),
        top_connected=top,
        avg_confidence=round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
    )
