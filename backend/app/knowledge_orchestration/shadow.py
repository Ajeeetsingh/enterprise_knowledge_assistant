"""Shadow Mode wiring for Worker Orchestration.

Plans queries via QueryPlannerService and orchestrates workers wrapping existing
providers. Never influences production answers. Does not modify prior packages.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_orchestration.metrics.runtime import OrchestrationMetrics
from app.knowledge_orchestration.orchestrator.orchestrator import KnowledgeOrchestrator
from app.knowledge_orchestration.registry.worker_registry import WorkerRegistry
from app.knowledge_orchestration.storage.json_store import OrchestrationJsonStore
from app.knowledge_orchestration.version import KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION
from app.query_planner.services.planner_service import QueryPlannerService

logger = get_logger(__name__)


class ShadowKnowledgeOrchestrationService:
    def __init__(
        self,
        *,
        orchestrator: KnowledgeOrchestrator | None = None,
        planner: QueryPlannerService | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._enabled = (
            settings.knowledge_orchestration_shadow_enabled if enabled is None else enabled
        )
        manager = KnowledgeIndexManager()
        registry = WorkerRegistry.with_defaults(index_manager=manager)
        self._orchestrator = orchestrator or KnowledgeOrchestrator(
            registry=registry,
            index_manager=manager,
        )
        self._planner = planner or QueryPlannerService(index_manager=manager)
        self._store = OrchestrationJsonStore(settings.indexes_path / "knowledge_orchestration")
        self._metrics = OrchestrationMetrics()
        self._wrapped = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def orchestrator(self) -> KnowledgeOrchestrator:
        return self._orchestrator

    def analyze_query(self, query: str) -> None:
        if not self._enabled or not query:
            return
        try:
            plan = self._planner.plan(query, persist=False)
            result = self._orchestrator.orchestrate(plan)
            self._metrics.record(result.worker_evidence)
            self._store.append(result.to_dict())
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge orchestration failed",
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
                "Worker Orchestration shadow wrapper installed on RagService",
                pipeline_version=KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Worker Orchestration shadow wrap failed",
                reason=type(exc).__name__,
            )


@lru_cache
def get_shadow_knowledge_orchestration_service() -> ShadowKnowledgeOrchestrationService:
    service = ShadowKnowledgeOrchestrationService()
    if service.enabled:
        service.wrap_rag_service()
        log_with_fields(
            logger,
            logging.INFO,
            "Worker Orchestration shadow mode enabled",
            pipeline_version=KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION,
        )
    return service


def ensure_shadow_knowledge_orchestration_wired() -> None:
    get_shadow_knowledge_orchestration_service()
