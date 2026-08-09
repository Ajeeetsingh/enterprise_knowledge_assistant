"""Strategy selection — plans how retrieval SHOULD happen (never executes)."""

from __future__ import annotations

from app.query_planner.enums import ExpectedResultType, QueryIntent, RetrievalStrategy
from app.query_planner.models.types import IntentCandidate, QueryConstraints


class StrategyBuilder:
    def build(
        self,
        intents: list[IntentCandidate],
        required_indexes: list[str],
        constraints: QueryConstraints,
    ) -> tuple[str, str, str]:
        """Return (preferred_strategy, fallback_strategy, expected_output)."""
        primary = intents[0].intent if intents else QueryIntent.UNKNOWN.value
        index_set = set(required_indexes)

        expected = self._expected_output(primary)

        if primary == QueryIntent.METADATA_SEARCH.value and index_set <= {"metadata"}:
            preferred = RetrievalStrategy.METADATA_ONLY.value
        elif "version" in index_set and "metadata" in index_set and "relationship" in index_set:
            preferred = RetrievalStrategy.METADATA_RELATIONSHIP_VERSION.value
        elif "version" in index_set and "metadata" in index_set:
            preferred = RetrievalStrategy.METADATA_VERSION.value
        elif "department" in index_set and "taxonomy" in index_set:
            preferred = RetrievalStrategy.DEPARTMENT_TAXONOMY.value
        elif "relationship" in index_set and "entity" in index_set:
            preferred = RetrievalStrategy.RELATIONSHIP_ENTITY.value
        elif "collection" in index_set and "metadata" in index_set:
            preferred = RetrievalStrategy.COLLECTION_METADATA.value
        elif "keyword" in index_set and "topic" in index_set and len(index_set) <= 3:
            preferred = RetrievalStrategy.KEYWORD_TOPIC.value
        elif primary == QueryIntent.RELATIONSHIP_QUERY.value:
            preferred = RetrievalStrategy.GRAPH_READY.value
        elif len(index_set) >= 4:
            preferred = RetrievalStrategy.HYBRID.value
        else:
            preferred = RetrievalStrategy.HYBRID.value

        if constraints.latest or constraints.oldest:
            if preferred == RetrievalStrategy.METADATA_ONLY.value:
                preferred = RetrievalStrategy.METADATA_VERSION.value

        fallback = RetrievalStrategy.FALLBACK_HYBRID.value
        if preferred == RetrievalStrategy.FALLBACK_HYBRID.value:
            fallback = RetrievalStrategy.KEYWORD_TOPIC.value

        return preferred, fallback, expected

    @staticmethod
    def _expected_output(intent: str) -> str:
        mapping = {
            QueryIntent.COUNT_QUERY.value: ExpectedResultType.COUNT.value,
            QueryIntent.SUMMARY_REQUEST.value: ExpectedResultType.SUMMARY.value,
            QueryIntent.COMPARISON.value: ExpectedResultType.COMPARISON.value,
            QueryIntent.RELATIONSHIP_QUERY.value: ExpectedResultType.RELATIONSHIPS.value,
            QueryIntent.NAVIGATION.value: ExpectedResultType.NAVIGATION.value,
            QueryIntent.METADATA_SEARCH.value: ExpectedResultType.METADATA.value,
        }
        return mapping.get(intent, ExpectedResultType.DOCUMENTS.value)
