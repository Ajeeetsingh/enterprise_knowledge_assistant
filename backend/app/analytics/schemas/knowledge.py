"""Pydantic models for knowledge analytics APIs (Phase 11.4)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import ChartSeries

if TYPE_CHECKING:
    from app.analytics.services.knowledge_analytics_service import (
        CollectionAnalyticsSnapshot,
        DocumentAnalyticsSnapshot,
        FreshnessAnalyticsSnapshot,
        KnowledgeGapSnapshot,
        KnowledgeOverviewSnapshot,
        SearchAnalyticsSnapshot,
    )


class KnowledgeOverviewResponse(BaseModel):
    """Administrator KPI summary for knowledge base health."""

    model_config = ConfigDict(from_attributes=True)

    total_documents: int = Field(ge=0)
    active_documents: int = Field(ge=0)
    stale_documents: int = Field(ge=0)
    unused_documents: int = Field(ge=0)
    average_document_views: float | None = Field(default=None, ge=0.0)
    average_citations_per_document: float | None = Field(default=None, ge=0.0)
    search_success_rate: float = Field(ge=0.0, le=100.0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: KnowledgeOverviewSnapshot,
    ) -> KnowledgeOverviewResponse:
        """Build an API response from a service-layer overview."""
        return cls.model_validate(snapshot)


class DocumentUsageItemResponse(BaseModel):
    """Single row in document usage analytics."""

    document_id: str
    filename: str
    collection: str
    view_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)


class DocumentAnalyticsResponse(BaseModel):
    """Document usage analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    most_viewed: list[DocumentUsageItemResponse]
    least_viewed: list[DocumentUsageItemResponse]
    total_most_viewed: int = Field(ge=0)
    total_least_viewed: int = Field(ge=0)
    average_document_views: float | None = Field(default=None, ge=0.0)
    average_citations_per_document: float | None = Field(default=None, ge=0.0)
    document_usage_trend: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: DocumentAnalyticsSnapshot) -> DocumentAnalyticsResponse:
        """Build an API response from a service-layer document snapshot."""
        return cls(
            most_viewed=[
                DocumentUsageItemResponse(
                    document_id=str(item["document_id"]),
                    filename=str(item["filename"]),
                    collection=str(item["collection"]),
                    view_count=int(item["view_count"]),
                    citation_count=int(item["citation_count"]),
                )
                for item in snapshot.most_viewed
            ],
            least_viewed=[
                DocumentUsageItemResponse(
                    document_id=str(item["document_id"]),
                    filename=str(item["filename"]),
                    collection=str(item["collection"]),
                    view_count=int(item["view_count"]),
                    citation_count=int(item["citation_count"]),
                )
                for item in snapshot.least_viewed
            ],
            total_most_viewed=snapshot.total_most_viewed,
            total_least_viewed=snapshot.total_least_viewed,
            average_document_views=snapshot.average_document_views,
            average_citations_per_document=snapshot.average_citations_per_document,
            document_usage_trend=snapshot.document_usage_trend,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class CollectionUsageItemResponse(BaseModel):
    """Single row in collection analytics."""

    collection: str
    document_count: int = Field(ge=0)
    usage_count: int = Field(ge=0)
    search_count: int = Field(ge=0)


class CollectionAnalyticsResponse(BaseModel):
    """Collection usage analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    items: list[CollectionUsageItemResponse]
    total: int = Field(ge=0)
    documents_per_collection: dict[str, int] = Field(default_factory=dict)
    collection_popularity: dict[str, int] = Field(default_factory=dict)
    retrieval_distribution: dict[str, int] = Field(default_factory=dict)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: CollectionAnalyticsSnapshot,
    ) -> CollectionAnalyticsResponse:
        """Build an API response from a service-layer collection snapshot."""
        return cls(
            items=[
                CollectionUsageItemResponse(
                    collection=str(item["collection"]),
                    document_count=int(item["document_count"]),
                    usage_count=int(item["usage_count"]),
                    search_count=int(item["search_count"]),
                )
                for item in snapshot.items
            ],
            total=snapshot.total,
            documents_per_collection=snapshot.documents_per_collection,
            collection_popularity=snapshot.collection_popularity,
            retrieval_distribution=snapshot.retrieval_distribution,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class SearchTopicItemResponse(BaseModel):
    """Single row in search topic analytics."""

    topic: str
    count: int = Field(ge=1)


class SearchAnalyticsResponse(BaseModel):
    """Search behavior analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    topics: list[SearchTopicItemResponse]
    documents: list[DocumentUsageItemResponse]
    collections: list[CollectionUsageItemResponse]
    total_topics: int = Field(ge=0)
    total_documents: int = Field(ge=0)
    total_collections: int = Field(ge=0)
    searches_with_no_results: int = Field(ge=0)
    search_success_rate: float = Field(ge=0.0, le=100.0)
    search_trend: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: SearchAnalyticsSnapshot) -> SearchAnalyticsResponse:
        """Build an API response from a service-layer search snapshot."""
        return cls(
            topics=[
                SearchTopicItemResponse(topic=str(item["topic"]), count=int(item["count"]))
                for item in snapshot.topics
            ],
            documents=[
                DocumentUsageItemResponse(
                    document_id=str(item["document_id"]),
                    filename=str(item["filename"]),
                    collection=str(item["collection"]),
                    view_count=int(item["view_count"]),
                    citation_count=int(item["citation_count"]),
                )
                for item in snapshot.documents
            ],
            collections=[
                CollectionUsageItemResponse(
                    collection=str(item["collection"]),
                    document_count=int(item["document_count"]),
                    usage_count=int(item["usage_count"]),
                    search_count=int(item["search_count"]),
                )
                for item in snapshot.collections
            ],
            total_topics=snapshot.total_topics,
            total_documents=snapshot.total_documents,
            total_collections=snapshot.total_collections,
            searches_with_no_results=snapshot.searches_with_no_results,
            search_success_rate=snapshot.search_success_rate,
            search_trend=snapshot.search_trend,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class KnowledgeGapItemResponse(BaseModel):
    """Single measurable knowledge gap fact."""

    category: str
    label: str
    count: int = Field(ge=0)


class KnowledgeGapResponse(BaseModel):
    """Knowledge gap analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    items: list[KnowledgeGapItemResponse]
    total: int = Field(ge=0)
    questions_without_documents: int = Field(ge=0)
    never_cited_documents: int = Field(ge=0)
    never_searched_documents: int = Field(ge=0)
    low_engagement_collections: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: KnowledgeGapSnapshot) -> KnowledgeGapResponse:
        """Build an API response from a service-layer gap snapshot."""
        return cls(
            items=[
                KnowledgeGapItemResponse(
                    category=str(item["category"]),
                    label=str(item["label"]),
                    count=int(item["count"]),
                )
                for item in snapshot.items
            ],
            total=snapshot.total,
            questions_without_documents=snapshot.questions_without_documents,
            never_cited_documents=snapshot.never_cited_documents,
            never_searched_documents=snapshot.never_searched_documents,
            low_engagement_collections=snapshot.low_engagement_collections,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class FreshnessItemResponse(BaseModel):
    """Single row in content freshness analytics."""

    document_id: str
    filename: str
    collection: str
    uploaded_at: datetime
    updated_at: datetime
    days_inactive: int = Field(ge=0)


class FreshnessAnalyticsResponse(BaseModel):
    """Content freshness analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    recent_uploads: list[FreshnessItemResponse]
    oldest_documents: list[FreshnessItemResponse]
    recently_updated: list[FreshnessItemResponse]
    longest_inactive: list[FreshnessItemResponse]
    total_recent_uploads: int = Field(ge=0)
    total_oldest_documents: int = Field(ge=0)
    total_recently_updated: int = Field(ge=0)
    total_longest_inactive: int = Field(ge=0)
    upload_trend: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: FreshnessAnalyticsSnapshot,
    ) -> FreshnessAnalyticsResponse:
        """Build an API response from a service-layer freshness snapshot."""
        def _item(row: dict[str, object]) -> FreshnessItemResponse:
            return FreshnessItemResponse(
                document_id=str(row["document_id"]),
                filename=str(row["filename"]),
                collection=str(row["collection"]),
                uploaded_at=row["uploaded_at"],  # type: ignore[arg-type]
                updated_at=row["updated_at"],  # type: ignore[arg-type]
                days_inactive=int(row["days_inactive"]),
            )

        return cls(
            recent_uploads=[_item(row) for row in snapshot.recent_uploads],
            oldest_documents=[_item(row) for row in snapshot.oldest_documents],
            recently_updated=[_item(row) for row in snapshot.recently_updated],
            longest_inactive=[_item(row) for row in snapshot.longest_inactive],
            total_recent_uploads=snapshot.total_recent_uploads,
            total_oldest_documents=snapshot.total_oldest_documents,
            total_recently_updated=snapshot.total_recently_updated,
            total_longest_inactive=snapshot.total_longest_inactive,
            upload_trend=snapshot.upload_trend,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )
