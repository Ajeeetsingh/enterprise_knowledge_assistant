"""Request-scoped RAG trace collector (diagnostics only)."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.logging import get_logger, log_with_fields
from app.rag.observability.models import (
    ChunkHitTrace,
    FinalContextChunk,
    PerQueryRetrievalTrace,
    RagDiagnosticReport,
    chunk_preview,
)
from app.rag.types import RetrievalResult

logger = get_logger(__name__)

_TLS = threading.local()


def is_diagnostics_enabled() -> bool:
    try:
        from app.config import get_settings

        settings = get_settings()
        return bool(
            getattr(settings, "rag_diagnostics_enabled", True)
            or getattr(settings, "routing_debug_logging", True)
        )
    except Exception:  # noqa: BLE001
        return True


def get_active_trace() -> "RagTraceSession | None":
    return getattr(_TLS, "trace", None)


def start_trace(question: str) -> "RagTraceSession":
    session = RagTraceSession(question=question)
    _TLS.trace = session
    return session


def finish_trace() -> RagDiagnosticReport | None:
    session = get_active_trace()
    _TLS.trace = None
    if session is None:
        return None
    return session.build_report()


@contextmanager
def trace_question(question: str) -> Iterator["RagTraceSession"]:
    session = start_trace(question)
    try:
        yield session
    finally:
        report = finish_trace()
        if report is not None:
            try:
                from app.rag.observability.reporter import (
                    render_diagnostic_report,
                    write_diagnostic_report,
                )

                text = render_diagnostic_report(report)
                path = write_diagnostic_report(report, text)
                log_with_fields(
                    logger,
                    logging.INFO,
                    "[RAG_DIAG] report_written",
                    path=str(path) if path else None,
                    question=question[:200],
                    chars=len(text),
                )
                # Do not dump the full report to the logging handlers — on Windows
                # consoles (cp1252) Unicode arrows/checkmarks in chunk text crash
                # the stream handler. The UTF-8 file is the source of truth.
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to write RAG diagnostic report: %s", type(exc).__name__)


def _filename(source: str) -> str:
    return source.replace("\\", "/").rsplit("/", 1)[-1]


def hit_from_result(
    result: RetrievalResult,
    *,
    rank: int,
    stage: str,
    found_by_queries: list[str] | None = None,
    selected: bool | None = None,
    bm25_score: float | None = None,
) -> ChunkHitTrace:
    return ChunkHitTrace(
        rank=rank,
        document=result.source,
        filename=_filename(result.source),
        page=result.page_number,
        chunk_id=result.chunk_id,
        chunk_type=result.chunk_type,
        preview=chunk_preview(result.content),
        dense_score=result.raw_cosine_score,
        bm25_score=bm25_score if bm25_score is not None else getattr(result, "bm25_score", None),
        fusion_score=result.fusion_score,
        metadata_bonus=result.metadata_bonus,
        metadata_final_score=result.final_score if stage in {"metadata", "merge", "per_query"} else None,
        cross_encoder_score=result.reranker_score,
        final_score=result.final_score,
        selected_for_context=selected,
        found_by_queries=list(found_by_queries or []),
        stage=stage,
    )


class RagTraceSession:
    """Mutable collector for one question's RAG pipeline."""

    def __init__(self, *, question: str) -> None:
        self.report = RagDiagnosticReport(question=question)
        self._chunk_to_queries: dict[str, list[str]] = {}
        self._current_query: str | None = None
        self._current_per_query: PerQueryRetrievalTrace | None = None
        self._bm25_by_chunk: dict[str, float] = {}

    def set_understanding(self, payload: dict[str, Any]) -> None:
        self.report.understanding = payload

    def set_expansion(self, queries: list[str], *, strategy: str | None) -> None:
        self.report.expansion_queries = list(queries)
        self.report.expansion_strategy = strategy

    def begin_retrieval_query(self, retrieval_query: str) -> None:
        self._current_query = retrieval_query
        self._current_per_query = PerQueryRetrievalTrace(retrieval_query=retrieval_query)
        self.report.per_query.append(self._current_per_query)

    def record_dense_sparse_fusion(
        self,
        *,
        dense_hits: list[Any],
        sparse_hits: list[Any],
        fused: list[Any],
    ) -> None:
        """Record pre-metadata hybrid stages for the active expanded query."""
        if self._current_per_query is None:
            return
        dense_traces: list[ChunkHitTrace] = []
        for rank, hit in enumerate(dense_hits[:20], start=1):
            chunk = hit.chunk
            dense_traces.append(
                ChunkHitTrace(
                    rank=rank,
                    document=chunk.source,
                    filename=_filename(chunk.source),
                    page=getattr(chunk, "page_number", None),
                    chunk_id=chunk.chunk_id,
                    chunk_type=getattr(getattr(chunk, "metadata", None), "chunk_type", None),
                    preview=chunk_preview(getattr(chunk, "content", "")),
                    dense_score=getattr(hit, "raw_cosine_score", None),
                    found_by_queries=[self._current_query] if self._current_query else [],
                    stage="dense",
                )
            )
        bm25_traces: list[ChunkHitTrace] = []
        for rank, hit in enumerate(sparse_hits[:20], start=1):
            chunk = hit.chunk
            score = getattr(hit, "bm25_score", None)
            if score is not None:
                self._bm25_by_chunk[chunk.chunk_id] = float(score)
            bm25_traces.append(
                ChunkHitTrace(
                    rank=rank,
                    document=chunk.source,
                    filename=_filename(chunk.source),
                    page=getattr(chunk, "page_number", None),
                    chunk_id=chunk.chunk_id,
                    chunk_type=getattr(getattr(chunk, "metadata", None), "chunk_type", None),
                    preview=chunk_preview(getattr(chunk, "content", "")),
                    bm25_score=score,
                    found_by_queries=[self._current_query] if self._current_query else [],
                    stage="bm25",
                )
            )
        fusion_traces: list[ChunkHitTrace] = []
        for rank, item in enumerate(fused[:20], start=1):
            chunk = item.chunk
            if item.bm25_score is not None:
                self._bm25_by_chunk[chunk.chunk_id] = float(item.bm25_score)
            fusion_traces.append(
                ChunkHitTrace(
                    rank=rank,
                    document=chunk.source,
                    filename=_filename(chunk.source),
                    page=getattr(chunk, "page_number", None),
                    chunk_id=chunk.chunk_id,
                    chunk_type=getattr(getattr(chunk, "metadata", None), "chunk_type", None),
                    preview=chunk_preview(getattr(chunk, "content", "")),
                    dense_score=item.raw_cosine_score,
                    bm25_score=item.bm25_score,
                    fusion_score=item.fusion_score,
                    found_by_queries=[self._current_query] if self._current_query else [],
                    stage="fusion",
                )
            )
        self._current_per_query.dense_hits = dense_traces
        self._current_per_query.bm25_hits = bm25_traces
        self._current_per_query.fusion_hits = fusion_traces

    def record_per_query_metadata_results(self, results: list[RetrievalResult]) -> None:
        if self._current_per_query is None or self._current_query is None:
            return
        traces: list[ChunkHitTrace] = []
        for rank, result in enumerate(results, start=1):
            self._remember_query(result.chunk_id, self._current_query)
            traces.append(
                hit_from_result(
                    result,
                    rank=rank,
                    stage="per_query",
                    found_by_queries=[self._current_query],
                    bm25_score=self._bm25_by_chunk.get(result.chunk_id),
                )
            )
        self._current_per_query.metadata_hits = traces

    def record_merge(self, results: list[RetrievalResult]) -> None:
        self.report.post_fusion_merge = [
            hit_from_result(
                result,
                rank=rank,
                stage="merge",
                found_by_queries=self._chunk_to_queries.get(result.chunk_id, []),
                bm25_score=self._bm25_by_chunk.get(result.chunk_id),
            )
            for rank, result in enumerate(results, start=1)
        ]

    def record_rerank(self, results: list[RetrievalResult]) -> None:
        self.report.post_rerank = [
            hit_from_result(
                result,
                rank=rank,
                stage="rerank",
                found_by_queries=self._chunk_to_queries.get(result.chunk_id, []),
                bm25_score=self._bm25_by_chunk.get(result.chunk_id),
            )
            for rank, result in enumerate(results, start=1)
        ]

    def record_final_context(self, results: list[RetrievalResult]) -> None:
        final_ids = {item.chunk_id for item in results}
        for hit in self.report.post_rerank:
            hit.selected_for_context = hit.chunk_id in final_ids
        for hit in self.report.post_fusion_merge:
            if hit.selected_for_context is None:
                hit.selected_for_context = hit.chunk_id in final_ids

        context: list[FinalContextChunk] = []
        total_chars = 0
        for order, result in enumerate(results, start=1):
            preview = chunk_preview(result.content)
            total_chars += len(result.content or "")
            context.append(
                FinalContextChunk(
                    order=order,
                    document=result.source,
                    page=result.page_number,
                    chunk_id=result.chunk_id,
                    chunk_type=result.chunk_type,
                    preview=preview,
                    found_by_queries=self._chunk_to_queries.get(result.chunk_id, []),
                )
            )
        self.report.final_context = context
        self.report.final_context_chars = total_chars
        self.report.final_context_approx_tokens = max(1, total_chars // 4) if total_chars else 0

    def record_answer_plan(self, payload: dict[str, Any]) -> None:
        """Record Phase 4A answer-structure plan (layout only)."""
        self.report.answer_plan = dict(payload or {})

    def record_evidence_graph(self, payload: dict[str, Any]) -> None:
        """Record Phase 4B organized evidence graph (regrouped retrieved chunks)."""
        self.report.evidence_graph = dict(payload or {})

    def record_answer_composition(self, payload: dict[str, Any]) -> None:
        """Record Phase 4C prioritized answer composition."""
        self.report.answer_composition = dict(payload or {})

    def record_answer_synthesis(self, payload: dict[str, Any]) -> None:
        """Record Phase 4F synthesis plan (concept composition for prompting)."""
        self.report.answer_synthesis = dict(payload or {})

    def record_response_layout(self, payload: dict[str, Any]) -> None:
        """Record Phase 5A response experience layout (presentation plan only)."""
        self.report.response_layout = dict(payload or {})

    def record_markdown_render(self, payload: dict[str, Any]) -> None:
        """Record Phase 5B enterprise markdown render diagnostics."""
        self.report.markdown_render = dict(payload or {})

    def record_presentation_polish(self, payload: dict[str, Any]) -> None:
        """Record Phase 5D presentation polish diagnostics."""
        self.report.presentation_polish = dict(payload or {})

    def record_presentation_finalize(self, payload: dict[str, Any]) -> None:
        """Record Phase 5E final consistency / UX polish diagnostics."""
        self.report.presentation_finalize = dict(payload or {})

    def record_gaqa_report(self, payload: dict[str, Any]) -> None:
        """Record Phase 4D GAQA validation report (answer unchanged)."""
        self.report.gaqa_report = dict(payload or {})

    def record_model_output(self, text: str | None) -> None:
        self.report.model_output = text

    def record_final_answer(self, text: str | None, *, answer_kind: str | None = None) -> None:
        self.report.final_answer = text
        self.report.answer_kind = answer_kind

    def add_error(self, message: str) -> None:
        self.report.errors.append(message)

    def _remember_query(self, chunk_id: str, query: str) -> None:
        bucket = self._chunk_to_queries.setdefault(chunk_id, [])
        if query not in bucket:
            bucket.append(query)

    def contributing_queries(self, chunk_id: str) -> list[str]:
        return list(self._chunk_to_queries.get(chunk_id, []))

    def evaluate_expected(self, indexed_chunks: list[Any] | None = None) -> None:
        """Populate missing-chunk verdicts from indexed corpus + stage membership."""
        from app.rag.observability.expected import evaluate_expected_chunks

        stages: dict[str, list[str]] = {
            "dense": [],
            "bm25": [],
            "fusion": [],
            "per_query": [],
            "merge": [h.chunk_id for h in self.report.post_fusion_merge],
            "rerank": [h.chunk_id for h in self.report.post_rerank],
            "final": [c.chunk_id for c in self.report.final_context],
        }
        for per in self.report.per_query:
            for hit in per.dense_hits:
                stages["dense"].append(hit.chunk_id)
            for hit in per.bm25_hits:
                stages["bm25"].append(hit.chunk_id)
            for hit in per.fusion_hits:
                stages["fusion"].append(hit.chunk_id)
            for hit in per.metadata_hits:
                stages["per_query"].append(hit.chunk_id)

        final_texts = [
            # Prefer full content from indexed chunks when available.
            next(
                (
                    getattr(chunk, "content", "")
                    for chunk in (indexed_chunks or [])
                    if getattr(chunk, "chunk_id", None) == item.chunk_id
                ),
                item.preview,
            )
            for item in self.report.final_context
        ]
        self.report.expected_chunk_verdicts = evaluate_expected_chunks(
            question=self.report.question,
            indexed_chunks=indexed_chunks or [],
            stages=stages,
            final_chunk_ids=stages["final"],
            rerank_chunk_ids=stages["rerank"],
            merge_chunk_ids=stages["merge"],
            final_chunk_texts=final_texts,
        )

    def build_report(self) -> RagDiagnosticReport:
        return self.report
