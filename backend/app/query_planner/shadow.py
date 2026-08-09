"""Shadow Mode wiring for the Intelligent Query Planner.

Wraps RagService.answer_question at runtime to optionally analyze queries.
Never influences retrieval results. Fail-open always.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.query_planner.services.planner_service import QueryPlannerService
from app.query_planner.version import QUERY_PLANNER_PIPELINE_VERSION

logger = get_logger(__name__)


class ShadowQueryPlannerService:
    """Analyze production queries in Shadow Mode without affecting answers."""

    def __init__(
        self,
        *,
        service: QueryPlannerService | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._enabled = (
            settings.query_planner_shadow_enabled if enabled is None else enabled
        )
        if service is not None:
            self._service = service
        else:
            self._service = QueryPlannerService.with_default_store(settings.indexes_path)
        self._wrapped = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def service(self) -> QueryPlannerService:
        return self._service

    def analyze(self, query: str) -> None:
        if not self._enabled or not query:
            return
        try:
            self._service.plan(query, persist=True)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow query planner failed",
                reason=type(exc).__name__,
            )

    def wrap_rag_service(self) -> None:
        """Install a fail-open shadow wrapper around RagService.answer_question."""
        if not self._enabled or self._wrapped:
            return
        try:
            from app.services.rag_service import get_rag_service

            rag = get_rag_service()
            original = rag.answer_question

            def _wrapped(
                question: str,
                role: str,
                authorized_sources: frozenset[str] | None = None,
                *,
                conversation_history: str | None = None,
            ) -> Any:
                try:
                    self.analyze(question)
                except Exception:  # noqa: BLE001
                    pass
                return original(
                    question,
                    role,
                    authorized_sources,
                    conversation_history=conversation_history,
                )

            rag.answer_question = _wrapped  # type: ignore[method-assign]
            self._wrapped = True
            log_with_fields(
                logger,
                logging.INFO,
                "Query Planner shadow wrapper installed on RagService",
                pipeline_version=QUERY_PLANNER_PIPELINE_VERSION,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Query Planner shadow wrap failed",
                reason=type(exc).__name__,
            )


@lru_cache
def get_shadow_query_planner_service() -> ShadowQueryPlannerService:
    service = ShadowQueryPlannerService()
    if service.enabled:
        service.wrap_rag_service()
        log_with_fields(
            logger,
            logging.INFO,
            "Intelligent Query Planner shadow mode enabled",
            pipeline_version=QUERY_PLANNER_PIPELINE_VERSION,
        )
    return service


def ensure_shadow_query_planner_wired() -> None:
    get_shadow_query_planner_service()
