"""Select and dispatch providers from a QueryExecutionPlan."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.knowledge_execution.models.types import ProviderResult
from app.knowledge_execution.providers.base import IndexProvider
from app.query_planner.models.types import QueryExecutionPlan


class ExecutionDispatcher:
    """Choose providers from plan.required_indexes and execute fault-tolerantly."""

    def __init__(
        self,
        providers: dict[str, IndexProvider],
        *,
        max_workers: int = 8,
    ) -> None:
        self._providers = providers
        self._max_workers = max_workers

    def select(self, plan: QueryExecutionPlan) -> list[IndexProvider]:
        names = list(plan.required_indexes or [])
        if not names:
            # Fallback Hybrid — still execute without modifying the plan object fields.
            names = ["keyword", "metadata"]
        selected: list[IndexProvider] = []
        seen: set[str] = set()
        for name in names:
            if name in seen:
                continue
            provider = self._providers.get(name)
            if provider is not None:
                selected.append(provider)
                seen.add(name)
        return selected

    def execute_parallel(self, plan: QueryExecutionPlan) -> list[ProviderResult]:
        selected = self.select(plan)
        if not selected:
            return []
        if len(selected) == 1:
            return [selected[0].execute(plan)]

        results: list[ProviderResult] = []
        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(selected))) as pool:
            futures = {pool.submit(provider.execute, plan): provider.name for provider in selected}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        ProviderResult(
                            provider_name=name,
                            success=False,
                            error=type(exc).__name__,
                        )
                    )
        # Stable order by provider name for determinism in tests/console
        order = {provider.name: index for index, provider in enumerate(selected)}
        results.sort(key=lambda item: order.get(item.provider_name, 999))
        return results
