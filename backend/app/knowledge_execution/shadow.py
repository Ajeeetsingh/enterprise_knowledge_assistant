"""Shadow Mode wiring for the Knowledge Execution Engine.

Consumes QueryExecutionPlans (via QueryPlannerService API) and executes them
against Hybrid Knowledge Indexes. Never influences production answers.
Does not modify Query Planner / Hybrid Index packages.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.knowledge_execution.coordinators.coordinator import ExecutionCoordinator
from app.knowledge_execution.version import KNOWLEDGE_EXECUTION_PIPELINE_VERSION
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan
from app.query_planner.services.planner_service import QueryPlannerService

logger = get_logger(__name__)


class ShadowKnowledgeExecutionService:
    """Execute QueryExecutionPlans in Shadow Mode without affecting answers."""

    def __init__(
        self,
        *,
        coordinator: ExecutionCoordinator | None = None,
        planner_service: QueryPlannerService | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._enabled = (
            settings.knowledge_execution_shadow_enabled if enabled is None else enabled
        )
        manager = KnowledgeIndexManager()
        self._planner = planner_service or QueryPlannerService(index_manager=manager)
        if coordinator is not None:
            self._coordinator = coordinator
        else:
            self._coordinator = ExecutionCoordinator.with_default_store(
                settings.indexes_path,
                index_manager=manager,
            )
        self._wrapped = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def coordinator(self) -> ExecutionCoordinator:
        return self._coordinator

    def execute_plan(self, plan: QueryExecutionPlan) -> None:
        if not self._enabled:
            return
        try:
            self._coordinator.execute(plan, persist=True)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge execution failed",
                reason=type(exc).__name__,
                plan_id=getattr(plan, "plan_id", None),
            )

    def analyze_query(self, query: str) -> None:
        """Obtain a plan (without mutating planner packages) and execute it."""
        if not self._enabled or not query:
            return
        try:
            plan = self._planner.plan(query, persist=False)
            self.execute_plan(plan)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge execution analyze failed",
                reason=type(exc).__name__,
            )

    def wrap_rag_service(self) -> None:
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
                    self.analyze_query(question)
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
                "Knowledge Execution Engine shadow wrapper installed on RagService",
                pipeline_version=KNOWLEDGE_EXECUTION_PIPELINE_VERSION,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Knowledge Execution Engine shadow wrap failed",
                reason=type(exc).__name__,
            )


@lru_cache
def get_shadow_knowledge_execution_service() -> ShadowKnowledgeExecutionService:
    service = ShadowKnowledgeExecutionService()
    if service.enabled:
        service.wrap_rag_service()
        log_with_fields(
            logger,
            logging.INFO,
            "Knowledge Execution Engine shadow mode enabled",
            pipeline_version=KNOWLEDGE_EXECUTION_PIPELINE_VERSION,
        )
    return service


def ensure_shadow_knowledge_execution_wired() -> None:
    get_shadow_knowledge_execution_service()
