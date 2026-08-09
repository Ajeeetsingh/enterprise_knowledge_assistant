"""Temporary structured routing/RAG debug logs for acceptance testing.

Enable with ROUTING_DEBUG_LOGGING=true (default true in development).
Safe to leave on during Phase 1 acceptance; does not alter answers.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.core.logging import get_logger, log_with_fields

logger = get_logger(__name__)


def _enabled() -> bool:
    try:
        from app.config import get_settings

        return bool(getattr(get_settings(), "routing_debug_logging", True))
    except Exception:  # noqa: BLE001
        return True


def log_routing_stage(
    *,
    question: str,
    route: str,
    method: str,
    confidence: float,
    document_score: float,
    general_score: float,
    signals: Iterable[str],
    rag_selected: bool,
) -> None:
    if not _enabled():
        return
    log_with_fields(
        logger,
        logging.INFO,
        "[ROUTING_DEBUG] classification",
        question=(question or "")[:240],
        route=route,
        method=method,
        confidence=confidence,
        document_score=document_score,
        general_score=general_score,
        signals=list(signals),
        rag_selected=rag_selected,
    )


def log_rag_retrieval_stage(
    *,
    question: str,
    chunk_count: int,
    top_documents: list[dict[str, Any]],
    prompt_context_chars: int | None = None,
    response_type: str | None = None,
) -> None:
    if not _enabled():
        return
    log_with_fields(
        logger,
        logging.INFO,
        "[ROUTING_DEBUG] retrieval",
        question=(question or "")[:240],
        chunk_count=chunk_count,
        top_documents=top_documents,
        prompt_context_chars=prompt_context_chars,
        response_type=response_type,
    )


def log_final_response_type(*, question: str, answer_kind: str, rag_executed: bool) -> None:
    if not _enabled():
        return
    log_with_fields(
        logger,
        logging.INFO,
        "[ROUTING_DEBUG] response",
        question=(question or "")[:240],
        answer_kind=answer_kind,
        rag_executed=rag_executed,
    )


def log_query_understanding_stage(
    *,
    original_question: str,
    intent: str,
    entities: list[str],
    concepts: list[str],
    likely_documents: list[str],
    retrieval_queries: list[str],
    expansion_strategy: str,
    confidence: float,
    domain: str = "",
    actions: list[str] | None = None,
) -> None:
    if not _enabled():
        return
    log_with_fields(
        logger,
        logging.INFO,
        "[ROUTING_DEBUG] query_understanding",
        original_question=(original_question or "")[:240],
        intent=intent,
        entities=entities,
        concepts=concepts,
        actions=list(actions or []),
        domain=domain,
        likely_documents=likely_documents,
        retrieval_queries=retrieval_queries,
        expansion_strategy=expansion_strategy,
        confidence=confidence,
        generated_query_count=len(retrieval_queries),
    )
