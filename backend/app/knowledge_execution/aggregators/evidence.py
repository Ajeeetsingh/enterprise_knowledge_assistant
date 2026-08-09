"""Merge and normalize evidence across providers."""

from __future__ import annotations

from collections import defaultdict

from app.knowledge_execution.models.types import EvidenceItem, ProviderResult


class EvidenceAggregator:
    """Deduplicate evidence and group by document while preserving explainability."""

    def aggregate(self, provider_results: list[ProviderResult]) -> dict[str, list[EvidenceItem]]:
        by_document: dict[str, list[EvidenceItem]] = defaultdict(list)
        seen: set[tuple[str, str, str, str]] = set()
        for result in provider_results:
            if not result.success:
                continue
            for item in result.evidence:
                key = (
                    item.document_id,
                    item.source_index,
                    item.matched_field,
                    str(item.metadata.get("query")),
                )
                if key in seen:
                    continue
                seen.add(key)
                # Normalize score into [0, 1]
                item.evidence_score = max(0.0, min(1.0, float(item.evidence_score)))
                item.confidence = max(0.0, min(1.0, float(item.confidence)))
                by_document[item.document_id].append(item)
        return dict(by_document)

    def flatten(self, grouped: dict[str, list[EvidenceItem]]) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for evidence in grouped.values():
            items.extend(evidence)
        return items
