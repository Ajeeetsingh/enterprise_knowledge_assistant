"""Read-only knowledge analytics queries over documents, audit, and chat data.

Aggregates from ``Document``, ``AuditLog``, ``Conversation``, and ``Message``
only. Collections are derived from document ``department`` (or ``tenant_id``)
because no dedicated collection table exists yet.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.message import Message
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.documents.status import DocumentStatus

UNCATEGORIZED_COLLECTION = "Uncategorized"
INACTIVE_DOCUMENT_STATUSES = frozenset(
    {DocumentStatus.DELETED.value, DocumentStatus.FAILED.value}
)
DEFAULT_STALE_DAYS = 90


@dataclass(frozen=True)
class DocumentUsageRow:
    """Per-document usage metrics derived from citation activity."""

    document_id: uuid.UUID
    filename: str
    collection: str
    view_count: int
    citation_count: int


@dataclass(frozen=True)
class CollectionUsageRow:
    """Per-collection engagement metrics."""

    collection: str
    document_count: int
    usage_count: int
    search_count: int


@dataclass(frozen=True)
class SearchTopicRow:
    """Aggregated count for a recurring search topic."""

    topic: str
    count: int


@dataclass(frozen=True)
class KnowledgeGapRow:
    """Measurable knowledge gap fact."""

    category: str
    label: str
    count: int


@dataclass(frozen=True)
class FreshnessRow:
    """Document freshness metadata for reporting tables."""

    document_id: uuid.UUID
    filename: str
    collection: str
    uploaded_at: datetime
    updated_at: datetime
    days_inactive: int


class KnowledgeRepository:
    """Persistence queries for knowledge base analytics."""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        db: Session,
        *,
        audit_repository: AuditRepository | None = None,
        stale_days: int = DEFAULT_STALE_DAYS,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository or AuditRepository(db)
        self._stale_days = stale_days

    def count_total_documents(self) -> int:
        """Return all non-deleted documents."""
        return self._count_documents()

    def count_active_documents(self) -> int:
        """Return documents in searchable lifecycle states."""
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
        )
        return self._db.scalar(query) or 0

    def count_stale_documents(self, context: AnalyticsContext) -> int:
        """Return active documents not updated within the stale threshold."""
        cutoff = context.end_date - timedelta(days=self._stale_days)
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .where(Document.updated_at < cutoff)
        )
        return self._db.scalar(query) or 0

    def count_unused_documents(self, context: AnalyticsContext) -> int:
        """Return active documents with zero citations in *context*."""
        cited_filenames = set(self._build_citation_counter(context).keys())
        documents = self._list_active_documents()
        return sum(
            1
            for document in documents
            if document.filename.lower() not in cited_filenames
        )

    def average_document_views(self, context: AnalyticsContext) -> float | None:
        """Return average citation count per active document in *context*."""
        counter = self._build_citation_counter(context)
        if not counter:
            return None
        return sum(counter.values()) / len(counter)

    def average_citations_per_document(self, context: AnalyticsContext) -> float | None:
        """Return average citations per cited document in *context*."""
        counter = self._build_citation_counter(context)
        if not counter:
            return None
        return sum(counter.values()) / len(counter)

    def list_top_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[DocumentUsageRow], int]:
        """Return most cited documents in *context*."""
        return self._rank_document_usage(context, limit=limit, offset=offset, reverse=True)

    def list_least_viewed_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[DocumentUsageRow], int]:
        """Return least cited active documents in *context*."""
        return self._rank_document_usage(context, limit=limit, offset=offset, reverse=False)

    def documents_per_collection(self) -> dict[str, int]:
        """Return document counts grouped by derived collection."""
        counter: Counter[str] = Counter()
        for document in self._list_active_documents():
            counter[self._collection_key(document)] += 1
        return dict(counter.most_common())

    def collection_popularity(self, context: AnalyticsContext) -> dict[str, int]:
        """Return citation counts grouped by document collection."""
        counter: Counter[str] = Counter()
        documents_by_filename = self._documents_by_filename_lower()
        for source, count in self._build_citation_counter(context).items():
            document = documents_by_filename.get(source)
            collection = self._collection_key(document) if document else UNCATEGORIZED_COLLECTION
            counter[collection] += count
        return dict(counter.most_common())

    def collection_usage(self, context: AnalyticsContext) -> list[CollectionUsageRow]:
        """Return per-collection document and citation usage."""
        documents_per = self.documents_per_collection()
        popularity = self.collection_popularity(context)
        search_counts = self.searches_by_collection(context)
        collections = sorted(
            set(documents_per) | set(popularity) | set(search_counts),
            key=lambda name: popularity.get(name, 0),
            reverse=True,
        )
        return [
            CollectionUsageRow(
                collection=name,
                document_count=documents_per.get(name, 0),
                usage_count=popularity.get(name, 0),
                search_count=search_counts.get(name, 0),
            )
            for name in collections
        ]

    def searches_by_collection(self, context: AnalyticsContext) -> dict[str, int]:
        """Return search counts grouped by cited collection within *context*."""
        counter: Counter[str] = Counter()
        documents_by_filename = self._documents_by_filename_lower()
        for message in self._list_user_messages(context):
            normalized = " ".join(message.strip().split()).lower()
            if not normalized:
                continue
            for document in documents_by_filename.values():
                if document.filename.lower() in normalized:
                    counter[self._collection_key(document)] += 1
                    break
        return dict(counter.most_common())

    def retrieval_distribution_by_collection(
        self,
        context: AnalyticsContext,
    ) -> dict[str, int]:
        """Return citation retrieval counts grouped by collection."""
        return self.collection_popularity(context)

    def list_search_topics(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[SearchTopicRow], int]:
        """Return the most common user search topics in *context*."""
        counter: Counter[str] = Counter()
        for content in self._list_user_messages(context):
            normalized = " ".join(str(content).strip().split())
            if normalized:
                counter[normalized] += 1
        ranked = [
            SearchTopicRow(topic=topic, count=count)
            for topic, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_searched_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[DocumentUsageRow], int]:
        """Return documents ranked by citation-based search activity."""
        return self.list_top_documents(context, limit=limit, offset=offset)

    def list_searched_collections(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[CollectionUsageRow], int]:
        """Return collections ranked by citation usage."""
        rows = self.collection_usage(context)
        total = len(rows)
        return rows[offset : offset + limit], total

    def count_searches(self, context: AnalyticsContext) -> int:
        """Return total chat questions in *context*."""
        return self._count_events(AnalyticsEvents.CHAT_QUESTION, context)

    def count_searches_no_results(self, context: AnalyticsContext) -> int:
        """Return searches that produced no retrieved documents."""
        failures = self._count_events(AnalyticsEvents.CHAT_FAILURE, context)
        empty_responses = self._count_empty_responses(context)
        return failures + empty_responses

    def search_success_rate(self, context: AnalyticsContext) -> float:
        """Return percentage of searches with at least one retrieved document."""
        total = self.count_searches(context)
        if total == 0:
            return 0.0
        unsuccessful = self.count_searches_no_results(context)
        successful = max(total - unsuccessful, 0)
        return (successful / total) * 100.0

    def list_search_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        """Return audit timestamps for chat questions in *context*."""
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.event_type == AnalyticsEvents.CHAT_QUESTION)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_citation_usage_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        """Return timestamps only for messages that cited at least one document."""
        query = (
            select(Message)
            .where(Message.role == "assistant")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
            .order_by(Message.created_at.asc())
        )
        return [
            message.created_at
            for message in self._db.scalars(query)
            if message.citations
        ]

    def list_upload_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        """Return upload timestamps within *context*."""
        query = (
            select(Document.uploaded_at)
            .where(Document.uploaded_at >= context.start_date)
            .where(Document.uploaded_at <= context.end_date)
            .order_by(Document.uploaded_at.asc())
        )
        return list(self._db.scalars(query))

    def count_questions_without_documents(self, context: AnalyticsContext) -> int:
        """Return user questions that produced zero retrieved documents."""
        return self.count_searches_no_results(context)

    def list_repeated_failed_searches(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[SearchTopicRow], int]:
        """Return recurring retrieval failure reasons."""
        counter: Counter[str] = Counter()
        for metadata in self._fetch_event_metadata(AnalyticsEvents.CHAT_FAILURE, context):
            reason = str(metadata.get("reason") or "Unknown failure").strip()
            counter[reason or "Unknown failure"] += 1
        ranked = [
            SearchTopicRow(topic=reason, count=count)
            for reason, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_never_cited_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[DocumentUsageRow], int]:
        """Return active documents never cited in *context*."""
        cited = set(self._build_citation_counter(context).keys())
        rows = [
            DocumentUsageRow(
                document_id=document.id,
                filename=document.filename,
                collection=self._collection_key(document),
                view_count=0,
                citation_count=0,
            )
            for document in self._list_active_documents()
            if document.filename.lower() not in cited
        ]
        rows.sort(key=lambda row: row.filename.lower())
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_never_searched_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[DocumentUsageRow], int]:
        """Return active documents not referenced by user questions in *context*."""
        searched_filenames: set[str] = set()
        documents_by_filename = self._documents_by_filename_lower()
        for content in self._list_user_messages(context):
            normalized = str(content).lower()
            for filename in documents_by_filename:
                if filename in normalized:
                    searched_filenames.add(filename)
        rows = [
            DocumentUsageRow(
                document_id=document.id,
                filename=document.filename,
                collection=self._collection_key(document),
                view_count=0,
                citation_count=0,
            )
            for filename, document in documents_by_filename.items()
            if filename not in searched_filenames
        ]
        rows.sort(key=lambda row: row.filename.lower())
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_low_engagement_collections(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[CollectionUsageRow], int]:
        """Return collections with the lowest citation usage in *context*."""
        rows = sorted(
            self.collection_usage(context),
            key=lambda row: (row.usage_count, row.document_count),
        )
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_recent_uploads(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[FreshnessRow], int]:
        """Return documents uploaded within *context*."""
        query = (
            select(Document)
            .where(Document.uploaded_at >= context.start_date)
            .where(Document.uploaded_at <= context.end_date)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .order_by(Document.uploaded_at.desc())
        )
        documents = list(self._db.scalars(query))
        rows = [self._freshness_row(document, context.end_date) for document in documents]
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_oldest_documents(
        self,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[FreshnessRow], int]:
        """Return the oldest active documents by upload date."""
        query = (
            select(Document)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .order_by(Document.uploaded_at.asc())
        )
        documents = list(self._db.scalars(query))
        now = datetime.now(UTC)
        rows = [self._freshness_row(document, now) for document in documents]
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_recently_updated(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[FreshnessRow], int]:
        """Return documents updated within *context*."""
        query = (
            select(Document)
            .where(Document.updated_at >= context.start_date)
            .where(Document.updated_at <= context.end_date)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .order_by(Document.updated_at.desc())
        )
        documents = list(self._db.scalars(query))
        rows = [self._freshness_row(document, context.end_date) for document in documents]
        total = len(rows)
        return rows[offset : offset + limit], total

    def list_longest_inactive_documents(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[FreshnessRow], int]:
        """Return active documents with the longest time since last update."""
        query = (
            select(Document)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .order_by(Document.updated_at.asc())
        )
        documents = list(self._db.scalars(query))
        rows = [self._freshness_row(document, context.end_date) for document in documents]
        total = len(rows)
        return rows[offset : offset + limit], total

    def _count_documents(self) -> int:
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status != DocumentStatus.DELETED.value)
        )
        return self._db.scalar(query) or 0

    def _list_active_documents(self) -> list[Document]:
        query = (
            select(Document)
            .where(Document.status.not_in(tuple(INACTIVE_DOCUMENT_STATUSES)))
            .order_by(Document.filename.asc())
        )
        return list(self._db.scalars(query))

    def _documents_by_filename_lower(self) -> dict[str, Document]:
        return {
            document.filename.lower(): document
            for document in self._list_active_documents()
        }

    def _build_citation_counter(self, context: AnalyticsContext) -> dict[str, int]:
        counter: Counter[str] = Counter()
        query = (
            select(Message)
            .where(Message.role == "assistant")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
            .order_by(Message.created_at.asc())
        )
        for message in self._db.scalars(query):
            for citation in message.citations:
                if not isinstance(citation, dict):
                    continue
                source = str(citation.get("source") or "").strip()
                if source:
                    counter[source.lower()] += 1
        return dict(counter)

    def _rank_document_usage(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int,
        reverse: bool,
    ) -> tuple[list[DocumentUsageRow], int]:
        counter = self._build_citation_counter(context)
        documents_by_filename = self._documents_by_filename_lower()
        rows: list[DocumentUsageRow] = []

        for filename, count in counter.items():
            document = documents_by_filename.get(filename)
            if document is None:
                continue
            rows.append(
                DocumentUsageRow(
                    document_id=document.id,
                    filename=document.filename,
                    collection=self._collection_key(document),
                    view_count=count,
                    citation_count=count,
                )
            )

        if not reverse:
            cited_filenames = set(counter.keys())
            for document in self._list_active_documents():
                if document.filename.lower() in cited_filenames:
                    continue
                rows.append(
                    DocumentUsageRow(
                        document_id=document.id,
                        filename=document.filename,
                        collection=self._collection_key(document),
                        view_count=0,
                        citation_count=0,
                    )
                )

        rows.sort(
            key=lambda row: (row.view_count, row.filename.lower()),
            reverse=reverse,
        )
        total = len(rows)
        return rows[offset : offset + limit], total

    def _list_user_messages(self, context: AnalyticsContext) -> list[str]:
        query = (
            select(Message.content)
            .where(Message.role == "user")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
        )
        return [str(content) for content in self._db.scalars(query)]

    def _count_empty_responses(self, context: AnalyticsContext) -> int:
        metadata_rows = self._fetch_event_metadata(AnalyticsEvents.CHAT_RESPONSE, context)
        if metadata_rows:
            return sum(
                1 for row in metadata_rows if int(row.get("citation_count") or 0) == 0
            )
        query = (
            select(Message)
            .where(Message.role == "assistant")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
        )
        return sum(1 for message in self._db.scalars(query) if len(message.citations) == 0)

    def _count_events(self, event_type: str, context: AnalyticsContext) -> int:
        return self._audit_repository.count(
            filters=AuditSearchFilter(
                event_type=event_type,
                date_from=context.start_date,
                date_to=context.end_date,
            )
        )

    def _fetch_event_metadata(
        self,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[dict]:
        query = (
            select(AuditLog.event_metadata)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        rows = self._db.scalars(query).all()
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _collection_key(document: Document | None) -> str:
        if document is None:
            return UNCATEGORIZED_COLLECTION
        if document.department and document.department.strip():
            return document.department.strip()
        if document.tenant_id and document.tenant_id.strip():
            return document.tenant_id.strip()
        return UNCATEGORIZED_COLLECTION

    @staticmethod
    def _freshness_row(document: Document, anchor: datetime) -> FreshnessRow:
        anchor_utc = anchor.astimezone(UTC)
        updated_utc = document.updated_at.astimezone(UTC)
        days_inactive = max((anchor_utc - updated_utc).days, 0)
        return FreshnessRow(
            document_id=document.id,
            filename=document.filename,
            collection=KnowledgeRepository._collection_key(document),
            uploaded_at=document.uploaded_at,
            updated_at=document.updated_at,
            days_inactive=days_inactive,
        )
