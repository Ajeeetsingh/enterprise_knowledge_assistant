"""Internal diagnostics for the document management subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import IngestionPipelineBase
from app.ingestion.vector_store.base import VectorStore
from app.storage.interface import StorageAdapter


@dataclass(frozen=True)
class ComponentDiagnostic:
    """Readiness result for a single document subsystem component."""

    name: str
    ready: bool
    message: str


@dataclass(frozen=True)
class DocumentSubsystemDiagnostics:
    """Aggregated readiness report for document processing dependencies."""

    storage: ComponentDiagnostic
    vector_store: ComponentDiagnostic
    embedding_provider: ComponentDiagnostic
    pipeline: ComponentDiagnostic
    overall_ready: bool


class DocumentDiagnosticsService:
    """Verify document subsystem component readiness.

    Reusable by future health endpoints and operational tooling.
    Does not expose a public API in this phase.
    """

    def __init__(
        self,
        storage: StorageAdapter,
        vector_store: VectorStore,
        pipeline: IngestionPipelineBase,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self._storage = storage
        self._vector_store = vector_store
        self._pipeline = pipeline
        self._embedding_provider = embedding_provider

    def check_readiness(self) -> DocumentSubsystemDiagnostics:
        """Run readiness checks against all document processing components."""
        storage_diag = self._check_storage()
        vector_diag = self._check_vector_store()
        embedding_diag = self._check_embedding_provider()
        pipeline_diag = self._check_pipeline()
        overall = all(
            diag.ready
            for diag in (storage_diag, vector_diag, embedding_diag, pipeline_diag)
        )
        return DocumentSubsystemDiagnostics(
            storage=storage_diag,
            vector_store=vector_diag,
            embedding_provider=embedding_diag,
            pipeline=pipeline_diag,
            overall_ready=overall,
        )

    def _check_storage(self) -> ComponentDiagnostic:
        try:
            base_path = getattr(self._storage, "base_path", None)
            if base_path is None:
                return ComponentDiagnostic(
                    name="storage",
                    ready=True,
                    message="Storage adapter is configured.",
                )
            base_path.mkdir(parents=True, exist_ok=True)
            probe = base_path / ".diagnostics_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return ComponentDiagnostic(
                name="storage",
                ready=True,
                message="Storage path is writable.",
            )
        except OSError as exc:
            return ComponentDiagnostic(
                name="storage",
                ready=False,
                message=f"Storage unavailable: {type(exc).__name__}.",
            )

    def _check_vector_store(self) -> ComponentDiagnostic:
        try:
            _ = self._vector_store.size
            return ComponentDiagnostic(
                name="vector_store",
                ready=True,
                message="Vector store is accessible.",
            )
        except Exception as exc:
            return ComponentDiagnostic(
                name="vector_store",
                ready=False,
                message=f"Vector store unavailable: {type(exc).__name__}.",
            )

    def _check_embedding_provider(self) -> ComponentDiagnostic:
        if self._embedding_provider is None:
            return ComponentDiagnostic(
                name="embedding_provider",
                ready=True,
                message="Embedding provider not configured for direct check.",
            )
        try:
            _ = getattr(self._embedding_provider, "dimension", None)
            return ComponentDiagnostic(
                name="embedding_provider",
                ready=True,
                message="Embedding provider is configured.",
            )
        except Exception as exc:
            return ComponentDiagnostic(
                name="embedding_provider",
                ready=False,
                message=f"Embedding provider unavailable: {type(exc).__name__}.",
            )

    def _check_pipeline(self) -> ComponentDiagnostic:
        stages = getattr(self._pipeline, "stages", None)
        if stages is None:
            names = self._pipeline.stage_names
            if not names:
                return ComponentDiagnostic(
                    name="pipeline",
                    ready=False,
                    message="Ingestion pipeline has no stages.",
                )
            return ComponentDiagnostic(
                name="pipeline",
                ready=True,
                message=f"Ingestion pipeline configured with {len(names)} stages.",
            )
        if not stages:
            return ComponentDiagnostic(
                name="pipeline",
                ready=False,
                message="Ingestion pipeline has no stages.",
            )
        return ComponentDiagnostic(
            name="pipeline",
            ready=True,
            message=f"Ingestion pipeline configured with {len(stages)} stages.",
        )
