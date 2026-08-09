"""Build execution diagnostics from provider results."""

from __future__ import annotations

from app.knowledge_execution.models.types import ExecutionDiagnostics, ProviderResult
from app.knowledge_execution.providers.base import IndexProvider


class DiagnosticsBuilder:
    def build(
        self,
        *,
        selected: list[IndexProvider],
        provider_results: list[ProviderResult],
    ) -> ExecutionDiagnostics:
        succeeded = [item.provider_name for item in provider_results if item.success]
        failed = [
            f"{item.provider_name}:{item.error or 'error'}"
            for item in provider_results
            if not item.success
        ]
        timeline = {item.provider_name: round(item.elapsed_ms, 4) for item in provider_results}
        notes = []
        if failed:
            notes.append("One or more providers failed; remaining evidence retained.")
        if not provider_results:
            notes.append("No providers executed.")
        return ExecutionDiagnostics(
            providers_selected=[provider.name for provider in selected],
            providers_succeeded=succeeded,
            providers_failed=[item.provider_name for item in provider_results if not item.success],
            provider_timeline_ms=timeline,
            notes=notes,
            warnings=["provider_failure"] if failed else [],
            failures=failed,
        )
