"""Worker Registry — registration, discovery, capability lookup, health."""

from __future__ import annotations

from app.knowledge_orchestration.models.types import WorkerCapability, WorkerHealth
from app.knowledge_orchestration.workers.base import Worker
from app.knowledge_orchestration.workers.graph_worker import GraphWorker
from app.knowledge_orchestration.workers.index_workers import build_index_workers
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.query_planner.models.types import QueryExecutionPlan


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    def register(self, worker: Worker) -> None:
        self._workers[worker.id()] = worker

    def unregister(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

    def get(self, worker_id: str) -> Worker | None:
        return self._workers.get(worker_id)

    def list_workers(self) -> list[Worker]:
        return sorted(self._workers.values(), key=lambda worker: (worker.priority(), worker.id()))

    def discover(self) -> list[dict]:
        return [worker.diagnostics() for worker in self.list_workers()]

    def by_capability(self, capability_name: str) -> list[Worker]:
        matched = []
        for worker in self.list_workers():
            if any(cap.name == capability_name for cap in worker.capabilities()):
                matched.append(worker)
        return matched

    def eligible(self, plan: QueryExecutionPlan) -> list[Worker]:
        return [worker for worker in self.list_workers() if worker.supports(plan)]

    def health(self) -> dict[str, WorkerHealth]:
        return {worker.id(): worker.health() for worker in self.list_workers()}

    def metadata(self) -> list[dict]:
        rows = []
        for worker in self.list_workers():
            rows.append(
                {
                    "id": worker.id(),
                    "priority": worker.priority(),
                    "capabilities": [cap.to_dict() for cap in worker.capabilities()],
                    "health": worker.health().to_dict(),
                    "depends_on": worker.depends_on(),
                }
            )
        return rows

    @classmethod
    def with_defaults(
        cls,
        *,
        index_manager: KnowledgeIndexManager | None = None,
        graph_service: KnowledgeGraphService | None = None,
    ) -> WorkerRegistry:
        registry = cls()
        for worker in build_index_workers(index_manager):
            registry.register(worker)
        registry.register(GraphWorker(graph_service=graph_service or KnowledgeGraphService()))
        return registry
