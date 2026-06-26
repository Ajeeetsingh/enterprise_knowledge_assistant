"""Persisted audit helpers for chat workflows (Phase 7.5).

Question text, prompts, document contents, and LLM responses must never
appear in persisted audit metadata.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services.audit_service import AuditService, run_persisted_audit


def record_question_asked(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    query_length: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a chat question submission audit event."""
    conversation_key = str(conversation_id)
    metadata: dict[str, Any] = {
        "conversation_id": conversation_key,
        "query_length": query_length,
    }
    run_persisted_audit(
        audit_service.log_event(
            event_type="chat.question.asked",
            event_category=AuditEventCategory.CHAT,
            action="ask_question",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="conversation",
            resource_id=conversation_key,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    )


def record_answer_generated(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    citation_count: int,
    confidence_score: float | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a successful chat answer audit event."""
    conversation_key = str(conversation_id)
    metadata: dict[str, Any] = {
        "conversation_id": conversation_key,
        "citation_count": citation_count,
    }
    if confidence_score is not None:
        metadata["confidence_score"] = confidence_score

    run_persisted_audit(
        audit_service.log_event(
            event_type="chat.answer.generated",
            event_category=AuditEventCategory.CHAT,
            action="generate_answer",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="conversation",
            resource_id=conversation_key,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    )


def record_retrieval_failed(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a failed chat retrieval/generation audit event."""
    conversation_key = str(conversation_id)
    run_persisted_audit(
        audit_service.log_event(
            event_type="chat.retrieval.failed",
            event_category=AuditEventCategory.CHAT,
            action="retrieve",
            status=AuditStatus.FAILED,
            user_id=user_id,
            resource_type="conversation",
            resource_id=conversation_key,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "conversation_id": conversation_key,
                "reason": reason,
            },
        )
    )
