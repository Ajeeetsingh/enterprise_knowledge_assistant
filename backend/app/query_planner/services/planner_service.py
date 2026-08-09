"""High-level Query Planner service with optional shadow persistence."""

from __future__ import annotations

from pathlib import Path

from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan
from app.query_planner.planner.pipeline import QueryPlanner
from app.query_planner.storage.json_store import QueryPlanJsonStore


class QueryPlannerService:
    def __init__(
        self,
        *,
        planner: QueryPlanner | None = None,
        index_manager: KnowledgeIndexManager | None = None,
        store: QueryPlanJsonStore | None = None,
    ) -> None:
        manager = index_manager or KnowledgeIndexManager()
        self._planner = planner or QueryPlanner(index_manager=manager)
        self._store = store

    @property
    def planner(self) -> QueryPlanner:
        return self._planner

    def plan(self, query: str, *, persist: bool = False) -> QueryExecutionPlan:
        plan = self._planner.plan(query)
        if persist and self._store is not None:
            self._store.append(plan.to_dict())
        return plan

    def statistics(self) -> dict:
        return self._planner.statistics()

    @classmethod
    def with_default_store(cls, indexes_root: Path) -> QueryPlannerService:
        store = QueryPlanJsonStore(Path(indexes_root) / "query_planner")
        manager = KnowledgeIndexManager()
        return cls(index_manager=manager, store=store)
