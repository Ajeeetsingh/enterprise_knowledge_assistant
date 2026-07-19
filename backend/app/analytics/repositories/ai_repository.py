"""Read-only AI analytics queries over persisted chat and audit data.

Aggregates from ``AuditLog``, ``Conversation``, and ``Message`` only. Latency
fields may be enriched when future audit events include timing metadata.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.utils.aggregation import extract_metadata_values
from app.db.models.audit_log import AuditLog
from app.db.models.message import Message
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter


@dataclass(frozen=True)
class QuestionFrequencyRow:
    """Aggregated count for a recurring user question."""

    question: str
    count: int


@dataclass(frozen=True)
class FailureAnalysisRow:
    """Aggregated count for a retrieval failure reason."""

    reason: str
    count: int


@dataclass(frozen=True)
class AssistantMessageSnapshot:
    """Assistant message metadata used for quality analytics."""

    created_at: datetime
    citation_count: int
    confidence_score: float | None
    sources: tuple[str, ...]


class AIRepository:
    """Persistence queries for AI performance analytics."""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        db: Session,
        *,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository or AuditRepository(db)

    def count_questions(self, context: AnalyticsContext) -> int:
        """Return chat questions asked within *context*."""
        return self._count_events(AnalyticsEvents.CHAT_QUESTION, context)

    def count_responses(self, context: AnalyticsContext) -> int:
        """Return generated AI answers within *context*."""
        return self._count_events(AnalyticsEvents.CHAT_RESPONSE, context)

    def count_failures(self, context: AnalyticsContext) -> int:
        """Return retrieval/generation failures within *context*."""
        return self._count_events(AnalyticsEvents.CHAT_FAILURE, context)

    def list_event_timestamps(
        self,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[datetime]:
        """Return audit timestamps for *event_type* within *context*."""
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def get_answer_metadata_with_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[tuple[datetime, dict]]:
        """Return answer audit metadata paired with event timestamps."""
        query = (
            select(AuditLog.created_at, AuditLog.event_metadata)
            .where(AuditLog.event_type == AnalyticsEvents.CHAT_RESPONSE)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        rows = self._db.execute(query).all()
        return [
            (created_at, metadata)
            for created_at, metadata in rows
            if isinstance(metadata, dict)
        ]

    def get_answer_metadata(self, context: AnalyticsContext) -> list[dict]:
        """Return answer audit metadata rows within *context*."""
        return [metadata for _, metadata in self.get_answer_metadata_with_timestamps(context)]

    def get_failure_metadata(self, context: AnalyticsContext) -> list[dict]:
        """Return failure audit metadata rows within *context*."""
        return self._fetch_event_metadata(AnalyticsEvents.CHAT_FAILURE, context)

    def average_citation_count(self, context: AnalyticsContext) -> float | None:
        """Return average citations per generated answer."""
        values = extract_metadata_values(
            self.get_answer_metadata(context),
            "citation_count",
        )
        if not values:
            return None
        return sum(values) / len(values)

    def average_confidence_score(self, context: AnalyticsContext) -> float | None:
        """Return average confidence score from answer audit metadata."""
        audit_values = extract_metadata_values(
            self.get_answer_metadata(context),
            "confidence_score",
        )
        message_values = [
            snapshot.confidence_score
            for snapshot in self.list_assistant_messages(context)
            if snapshot.confidence_score is not None
        ]
        values = audit_values + message_values
        if not values:
            return None
        return sum(values) / len(values)

    def count_responses_without_citations(self, context: AnalyticsContext) -> int:
        """Return answers with zero citations."""
        metadata_rows = self.get_answer_metadata(context)
        if metadata_rows:
            return sum(
                1
                for row in metadata_rows
                if int(row.get("citation_count") or 0) == 0
            )
        return sum(
            1 for snapshot in self.list_assistant_messages(context) if snapshot.citation_count == 0
        )

    def count_empty_retrievals(self, context: AnalyticsContext) -> int:
        """Return responses where no documents were retrieved."""
        return self.count_responses_without_citations(context)

    def compute_response_time_seconds(self, context: AnalyticsContext) -> list[float]:
        """Estimate response latency from user-to-assistant message pairs."""
        return [seconds for _, seconds in self.compute_response_time_samples(context)]

    def compute_response_time_samples(
        self,
        context: AnalyticsContext,
    ) -> list[tuple[datetime, float]]:
        """Return assistant timestamps with estimated response latency."""
        query = (
            select(Message)
            .join(Message.conversation)
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
            .order_by(Message.conversation_id.asc(), Message.created_at.asc())
        )
        messages = list(self._db.scalars(query))
        samples: list[tuple[datetime, float]] = []
        pending_user_times: dict[uuid.UUID, datetime] = {}

        for message in messages:
            if message.role == "user":
                pending_user_times[message.conversation_id] = message.created_at
                continue
            if message.role != "assistant":
                continue
            user_time = pending_user_times.pop(message.conversation_id, None)
            if user_time is None:
                continue
            delta = (message.created_at - user_time).total_seconds()
            if delta >= 0:
                samples.append((message.created_at, delta))
        return samples

    def list_assistant_messages(self, context: AnalyticsContext) -> list[AssistantMessageSnapshot]:
        """Return assistant message metadata within *context*."""
        query = (
            select(Message)
            .where(Message.role == "assistant")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
            .order_by(Message.created_at.asc())
        )
        rows = list(self._db.scalars(query))
        snapshots: list[AssistantMessageSnapshot] = []
        for message in rows:
            sources = tuple(
                str(citation.get("source"))
                for citation in message.citations
                if isinstance(citation, dict) and citation.get("source")
            )
            snapshots.append(
                AssistantMessageSnapshot(
                    created_at=message.created_at,
                    citation_count=len(message.citations),
                    confidence_score=message.confidence_score,
                    sources=sources,
                )
            )
        return snapshots

    def list_top_questions(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[QuestionFrequencyRow], int]:
        """Return the most common user questions in *context*."""
        query = (
            select(Message.content)
            .where(Message.role == "user")
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
        )
        contents = list(self._db.scalars(query))
        counter: Counter[str] = Counter()
        for content in contents:
            normalized = " ".join(str(content).strip().split())
            if normalized:
                counter[normalized] += 1

        ranked = [
            QuestionFrequencyRow(question=question, count=count)
            for question, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_failure_reasons(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[FailureAnalysisRow], int]:
        """Return aggregated retrieval failure reasons."""
        counter: Counter[str] = Counter()
        for row in self.get_failure_metadata(context):
            reason = str(row.get("reason") or "Unknown failure").strip()
            counter[reason or "Unknown failure"] += 1

        ranked = [
            FailureAnalysisRow(reason=reason, count=count)
            for reason, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def citation_source_distribution(self, context: AnalyticsContext) -> dict[str, int]:
        """Return citation source counts grouped by document source."""
        counter: Counter[str] = Counter()
        for snapshot in self.list_assistant_messages(context):
            for source in snapshot.sources:
                counter[source] += 1
        return dict(counter.most_common())

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
