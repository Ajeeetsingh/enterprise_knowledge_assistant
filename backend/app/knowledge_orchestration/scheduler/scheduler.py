"""Scheduler — parallel/sequential groups, dependencies, budgets, timeouts."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from typing import Any, Callable

from app.knowledge_orchestration.models.types import (
    ExecutionSchedule,
    ScheduledWorker,
    WorkerEvidence,
)
from app.knowledge_orchestration.policies.failure import FailurePolicy
from app.knowledge_orchestration.workers.base import Worker
from app.query_planner.models.types import QueryExecutionPlan


class WorkerScheduler:
    def __init__(
        self,
        *,
        failure_policy: FailurePolicy | None = None,
        default_timeout_ms: float = 2000.0,
        budget_ms: float = 10000.0,
        max_workers: int = 8,
    ) -> None:
        self._failure_policy = failure_policy or FailurePolicy()
        self._default_timeout_ms = default_timeout_ms
        self._budget_ms = budget_ms
        self._max_workers = max_workers

    def build_schedule(self, workers: list[Worker]) -> ExecutionSchedule:
        # Topological groups by depends_on among eligible workers.
        ids = {worker.id() for worker in workers}
        remaining = {worker.id(): worker for worker in workers}
        deps = {
            worker.id(): [dep for dep in worker.depends_on() if dep in ids]
            for worker in workers
        }
        groups: list[list[str]] = []
        scheduled: list[ScheduledWorker] = []
        group_index = 0
        completed: set[str] = set()
        while remaining:
            ready = [
                worker_id
                for worker_id, worker in remaining.items()
                if all(dep in completed for dep in deps[worker_id])
            ]
            if not ready:
                # Break cycles by scheduling remaining by priority.
                ready = sorted(remaining.keys(), key=lambda wid: remaining[wid].priority())
            ready_sorted = sorted(ready, key=lambda wid: (remaining[wid].priority(), wid))
            groups.append(ready_sorted)
            for worker_id in ready_sorted:
                worker = remaining.pop(worker_id)
                scheduled.append(
                    ScheduledWorker(
                        worker_id=worker_id,
                        group=group_index,
                        depends_on=deps[worker_id],
                        timeout_ms=self._default_timeout_ms,
                        parallel=len(ready_sorted) > 1,
                    )
                )
                completed.add(worker_id)
            group_index += 1
        return ExecutionSchedule(workers=scheduled, groups=groups, budget_ms=self._budget_ms)

    def run(
        self,
        plan: QueryExecutionPlan,
        workers: list[Worker],
        *,
        context_factory: Callable[[list[WorkerEvidence]], dict[str, Any]] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> tuple[list[WorkerEvidence], ExecutionSchedule, list[dict[str, Any]]]:
        schedule = self.build_schedule(workers)
        by_id = {worker.id(): worker for worker in workers}
        results: list[WorkerEvidence] = []
        timeline: list[dict[str, Any]] = []
        started_all = time.perf_counter()

        for group in schedule.groups:
            if cancel_check and cancel_check():
                for worker_id in group:
                    evidence = WorkerEvidence(
                        worker_id=worker_id,
                        success=False,
                        skipped=True,
                        error="soft_cancelled",
                    )
                    results.append(self._failure_policy.handle(evidence))
                    timeline.append(
                        {
                            "worker_id": worker_id,
                            "status": "skipped",
                            "reason": "soft_cancelled",
                        }
                    )
                continue

            elapsed_budget = (time.perf_counter() - started_all) * 1000
            if elapsed_budget >= schedule.budget_ms:
                for worker_id in group:
                    evidence = WorkerEvidence(
                        worker_id=worker_id,
                        success=False,
                        skipped=True,
                        error="budget_exhausted",
                    )
                    results.append(self._failure_policy.handle(evidence))
                    timeline.append(
                        {
                            "worker_id": worker_id,
                            "status": "skipped",
                            "reason": "budget_exhausted",
                        }
                    )
                continue

            context = context_factory(results) if context_factory else {}
            if len(group) == 1:
                worker_id = group[0]
                evidence = self._execute_one(
                    by_id[worker_id],
                    plan,
                    context=context,
                    timeout_ms=self._default_timeout_ms,
                )
                results.append(self._failure_policy.handle(evidence))
                timeline.append(self._timeline_entry(evidence))
            else:
                group_results = self._execute_parallel(
                    [by_id[worker_id] for worker_id in group],
                    plan,
                    context=context,
                    timeout_ms=self._default_timeout_ms,
                )
                for evidence in group_results:
                    results.append(self._failure_policy.handle(evidence))
                    timeline.append(self._timeline_entry(evidence))

        return results, schedule, timeline

    def _execute_one(
        self,
        worker: Worker,
        plan: QueryExecutionPlan,
        *,
        context: dict[str, Any],
        timeout_ms: float,
    ) -> WorkerEvidence:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.execute, plan, context=context)
            try:
                return future.result(timeout=max(0.05, timeout_ms / 1000.0))
            except FuturesTimeoutError:
                return WorkerEvidence(
                    worker_id=worker.id(),
                    success=False,
                    timed_out=True,
                    error="timeout",
                    source_attribution=worker.id(),
                )
            except Exception as exc:  # noqa: BLE001
                return WorkerEvidence(
                    worker_id=worker.id(),
                    success=False,
                    error=type(exc).__name__,
                    source_attribution=worker.id(),
                )

    def _execute_parallel(
        self,
        workers: list[Worker],
        plan: QueryExecutionPlan,
        *,
        context: dict[str, Any],
        timeout_ms: float,
    ) -> list[WorkerEvidence]:
        results: list[WorkerEvidence] = []
        timeout_s = max(0.05, timeout_ms / 1000.0)
        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(workers))) as pool:
            futures = {
                pool.submit(worker.execute, plan, context=context): worker.id()
                for worker in workers
            }
            pending = set(futures.keys())
            deadline = time.perf_counter() + timeout_s
            try:
                for future in as_completed(futures, timeout=timeout_s):
                    pending.discard(future)
                    worker_id = futures[future]
                    try:
                        results.append(future.result(timeout=0))
                    except Exception as exc:  # noqa: BLE001
                        results.append(
                            WorkerEvidence(
                                worker_id=worker_id,
                                success=False,
                                error=type(exc).__name__,
                            )
                        )
                    if time.perf_counter() >= deadline:
                        break
            except FuturesTimeoutError:
                pass

            for future in pending:
                worker_id = futures[future]
                results.append(
                    WorkerEvidence(
                        worker_id=worker_id,
                        success=False,
                        timed_out=True,
                        error="timeout",
                    )
                )
        order = {worker.id(): index for index, worker in enumerate(workers)}
        results.sort(key=lambda item: order.get(item.worker_id, 999))
        return results

    @staticmethod
    def _timeline_entry(evidence: WorkerEvidence) -> dict[str, Any]:
        status = "ok"
        if evidence.skipped:
            status = "skipped"
        elif evidence.timed_out:
            status = "timeout"
        elif not evidence.success:
            status = "failed"
        return {
            "worker_id": evidence.worker_id,
            "status": status,
            "elapsed_ms": evidence.elapsed_ms,
            "evidence_count": len(evidence.evidence_items),
            "error": evidence.error,
        }
