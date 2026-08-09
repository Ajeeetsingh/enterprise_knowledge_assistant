"""Coordinate plan → execute → persist without mutating the plan."""

from __future__ import annotations

from pathlib import Path

from app.knowledge_execution.executor.engine import KnowledgeExecutionEngine
from app.knowledge_execution.models.types import CandidateEvidenceSet
from app.knowledge_execution.storage.json_store import ExecutionResultJsonStore
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan


class ExecutionCoordinator:
    def __init__(
        self,
        *,
        engine: KnowledgeExecutionEngine | None = None,
        index_manager: KnowledgeIndexManager | None = None,
        store: ExecutionResultJsonStore | None = None,
    ) -> None:
        manager = index_manager or KnowledgeIndexManager()
        self._engine = engine or KnowledgeExecutionEngine(index_manager=manager)
        self._store = store

    @property
    def engine(self) -> KnowledgeExecutionEngine:
        return self._engine

    def execute(
        self,
        plan: QueryExecutionPlan,
        *,
        persist: bool = False,
    ) -> CandidateEvidenceSet:
        # Consume the plan as-is; never mutate fields.
        result = self._engine.execute(plan)
        if persist and self._store is not None:
            self._store.append(result.to_dict())
        return result

    @classmethod
    def with_default_store(
        cls,
        indexes_root: Path,
        *,
        index_manager: KnowledgeIndexManager | None = None,
    ) -> ExecutionCoordinator:
        store = ExecutionResultJsonStore(Path(indexes_root) / "knowledge_execution")
        return cls(index_manager=index_manager, store=store)
