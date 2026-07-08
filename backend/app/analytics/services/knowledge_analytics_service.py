"""Knowledge analytics orchestration for administrator dashboards (Phase 11.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.knowledge_repository import KnowledgeRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.utils.aggregation import bucket_counts_by_day


@dataclass(frozen=True)
class KnowledgeOverviewSnapshot:
    """Service-layer knowledge analytics KPI snapshot."""

    total_documents: int
    active_documents: int
    stale_documents: int
    unused_documents: int
    average_document_views: float | None
    average_citations_per_document: float | None
    search_success_rate: float
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class DocumentAnalyticsSnapshot:
    """Service-layer document usage analytics snapshot."""

    most_viewed: list[dict[str, object]]
    least_viewed: list[dict[str, object]]
    total_most_viewed: int
    total_least_viewed: int
    average_document_views: float | None
    average_citations_per_document: float | None
    document_usage_trend: ChartSeries
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class CollectionAnalyticsSnapshot:
    """Service-layer collection analytics snapshot."""

    items: list[dict[str, object]]
    total: int
    documents_per_collection: dict[str, int]
    collection_popularity: dict[str, int]
    retrieval_distribution: dict[str, int]
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class SearchAnalyticsSnapshot:
    """Service-layer search behavior analytics snapshot."""

    topics: list[dict[str, object]]
    documents: list[dict[str, object]]
    collections: list[dict[str, object]]
    total_topics: int
    total_documents: int
    total_collections: int
    searches_with_no_results: int
    search_success_rate: float
    search_trend: ChartSeries
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class KnowledgeGapSnapshot:
    """Service-layer knowledge gap analytics snapshot."""

    items: list[dict[str, object]]
    total: int
    questions_without_documents: int
    never_cited_documents: int
    never_searched_documents: int
    low_engagement_collections: int
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class FreshnessAnalyticsSnapshot:
    """Service-layer content freshness analytics snapshot."""

    recent_uploads: list[dict[str, object]]
    oldest_documents: list[dict[str, object]]
    recently_updated: list[dict[str, object]]
    longest_inactive: list[dict[str, object]]
    total_recent_uploads: int
    total_oldest_documents: int
    total_recently_updated: int
    total_longest_inactive: int
    upload_trend: ChartSeries
    start_date: datetime
    end_date: datetime


class KnowledgeAnalyticsService:
    """Aggregate knowledge base health, usage, and freshness metrics."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self._repository = repository

    def get_overview(self, context: AnalyticsContext) -> KnowledgeOverviewSnapshot:
        """Return administrator KPIs for knowledge base health."""
        return KnowledgeOverviewSnapshot(
            total_documents=self._repository.count_total_documents(),
            active_documents=self._repository.count_active_documents(),
            stale_documents=self._repository.count_stale_documents(context),
            unused_documents=self._repository.count_unused_documents(context),
            average_document_views=self._round_optional(
                self._repository.average_document_views(context),
            ),
            average_citations_per_document=self._round_optional(
                self._repository.average_citations_per_document(context),
            ),
            search_success_rate=round(self._repository.search_success_rate(context), 2),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> DocumentAnalyticsSnapshot:
        """Return document usage analytics."""
        most_viewed, total_most = self._repository.list_top_documents(
            context,
            limit=limit,
            offset=offset,
        )
        least_viewed, total_least = self._repository.list_least_viewed_documents(
            context,
            limit=limit,
            offset=offset,
        )
        return DocumentAnalyticsSnapshot(
            most_viewed=[self._document_row(row) for row in most_viewed],
            least_viewed=[self._document_row(row) for row in least_viewed],
            total_most_viewed=total_most,
            total_least_viewed=total_least,
            average_document_views=self._round_optional(
                self._repository.average_document_views(context),
            ),
            average_citations_per_document=self._round_optional(
                self._repository.average_citations_per_document(context),
            ),
            document_usage_trend=self._series(
                "document_usage",
                bucket_counts_by_day(
                    self._repository.list_citation_usage_timestamps(context),
                ),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_collections(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> CollectionAnalyticsSnapshot:
        """Return collection usage analytics."""
        rows, total = self._repository.list_searched_collections(
            context,
            limit=limit,
            offset=offset,
        )
        return CollectionAnalyticsSnapshot(
            items=[self._collection_row(row) for row in rows],
            total=total,
            documents_per_collection=self._repository.documents_per_collection(),
            collection_popularity=self._repository.collection_popularity(context),
            retrieval_distribution=self._repository.retrieval_distribution_by_collection(
                context,
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_searches(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> SearchAnalyticsSnapshot:
        """Return search behavior analytics."""
        topics, total_topics = self._repository.list_search_topics(
            context,
            limit=limit,
            offset=offset,
        )
        documents, total_documents = self._repository.list_searched_documents(
            context,
            limit=limit,
            offset=offset,
        )
        collections, total_collections = self._repository.list_searched_collections(
            context,
            limit=limit,
            offset=offset,
        )
        return SearchAnalyticsSnapshot(
            topics=[self._topic_row(row) for row in topics],
            documents=[self._document_row(row) for row in documents],
            collections=[self._collection_row(row) for row in collections],
            total_topics=total_topics,
            total_documents=total_documents,
            total_collections=total_collections,
            searches_with_no_results=self._repository.count_searches_no_results(context),
            search_success_rate=round(self._repository.search_success_rate(context), 2),
            search_trend=self._series(
                AnalyticsEvents.CHAT_QUESTION,
                bucket_counts_by_day(self._repository.list_search_timestamps(context)),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_gaps(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> KnowledgeGapSnapshot:
        """Return measurable knowledge gap facts."""
        items: list[dict[str, object]] = []

        questions_without = self._repository.count_questions_without_documents(context)
        if questions_without:
            items.append(
                {
                    "category": "questions_without_documents",
                    "label": "Questions with no retrieved documents",
                    "count": questions_without,
                }
            )

        failed, _ = self._repository.list_repeated_failed_searches(
            context,
            limit=limit,
            offset=0,
        )
        for row in failed:
            items.append(
                {
                    "category": "failed_search",
                    "label": row.topic,
                    "count": row.count,
                }
            )

        never_cited, never_cited_total = self._repository.list_never_cited_documents(
            context,
            limit=limit,
            offset=offset,
        )
        for row in never_cited:
            items.append(
                {
                    "category": "never_cited_document",
                    "label": row.filename,
                    "count": 0,
                }
            )

        never_searched, never_searched_total = self._repository.list_never_searched_documents(
            context,
            limit=limit,
            offset=offset,
        )
        for row in never_searched:
            items.append(
                {
                    "category": "never_searched_document",
                    "label": row.filename,
                    "count": 0,
                }
            )

        low_engagement, low_engagement_total = self._repository.list_low_engagement_collections(
            context,
            limit=limit,
            offset=offset,
        )
        for row in low_engagement:
            items.append(
                {
                    "category": "low_engagement_collection",
                    "label": row.collection,
                    "count": row.usage_count,
                }
            )

        return KnowledgeGapSnapshot(
            items=items[offset : offset + limit],
            total=len(items),
            questions_without_documents=questions_without,
            never_cited_documents=never_cited_total,
            never_searched_documents=never_searched_total,
            low_engagement_collections=low_engagement_total,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_freshness(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> FreshnessAnalyticsSnapshot:
        """Return content freshness analytics."""
        recent_uploads, total_recent = self._repository.list_recent_uploads(
            context,
            limit=limit,
            offset=offset,
        )
        oldest_documents, total_oldest = self._repository.list_oldest_documents(
            limit=limit,
            offset=offset,
        )
        recently_updated, total_updated = self._repository.list_recently_updated(
            context,
            limit=limit,
            offset=offset,
        )
        longest_inactive, total_inactive = self._repository.list_longest_inactive_documents(
            context,
            limit=limit,
            offset=offset,
        )
        return FreshnessAnalyticsSnapshot(
            recent_uploads=[self._freshness_row(row) for row in recent_uploads],
            oldest_documents=[self._freshness_row(row) for row in oldest_documents],
            recently_updated=[self._freshness_row(row) for row in recently_updated],
            longest_inactive=[self._freshness_row(row) for row in longest_inactive],
            total_recent_uploads=total_recent,
            total_oldest_documents=total_oldest,
            total_recently_updated=total_updated,
            total_longest_inactive=total_inactive,
            upload_trend=self._series(
                AnalyticsEvents.DOCUMENT_UPLOAD,
                bucket_counts_by_day(self._repository.list_upload_timestamps(context)),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    @staticmethod
    def _series(event_type: str, points: dict[str, float | int]) -> ChartSeries:
        normalized = {key: int(value) for key, value in points.items()}
        return ChartSeries(event_type=event_type, points=normalized)

    @staticmethod
    def _round_optional(value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 2)

    @staticmethod
    def _document_row(row: object) -> dict[str, object]:
        return {
            "document_id": str(row.document_id),
            "filename": row.filename,
            "collection": row.collection,
            "view_count": row.view_count,
            "citation_count": row.citation_count,
        }

    @staticmethod
    def _collection_row(row: object) -> dict[str, object]:
        return {
            "collection": row.collection,
            "document_count": row.document_count,
            "usage_count": row.usage_count,
            "search_count": row.search_count,
        }

    @staticmethod
    def _topic_row(row: object) -> dict[str, object]:
        return {"topic": row.topic, "count": row.count}

    @staticmethod
    def _freshness_row(row: object) -> dict[str, object]:
        return {
            "document_id": str(row.document_id),
            "filename": row.filename,
            "collection": row.collection,
            "uploaded_at": row.uploaded_at,
            "updated_at": row.updated_at,
            "days_inactive": row.days_inactive,
        }


def build_knowledge_analytics_service(db: Session) -> KnowledgeAnalyticsService:
    """Construct a knowledge analytics service bound to the given database session."""
    return KnowledgeAnalyticsService(KnowledgeRepository(db))
