"""Data models for RAG diagnostic traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PREVIEW_CHARS = 400


def chunk_preview(text: str | None, *, limit: int = PREVIEW_CHARS) -> str:
    """Return a short preview of chunk text for diagnostics."""
    content = (text or "").strip().replace("\r\n", "\n")
    if len(content) <= limit:
        return content
    return content[:limit].rstrip() + "…"


@dataclass
class ChunkHitTrace:
    """One retrieved chunk at a specific pipeline stage."""

    rank: int
    document: str
    filename: str
    page: int | None
    chunk_id: str
    chunk_type: str | None
    preview: str
    dense_score: float | None = None
    bm25_score: float | None = None
    fusion_score: float | None = None
    metadata_bonus: float | None = None
    metadata_final_score: float | None = None
    cross_encoder_score: float | None = None
    final_score: float | None = None
    selected_for_context: bool | None = None
    found_by_queries: list[str] = field(default_factory=list)
    stage: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "document": self.document,
            "filename": self.filename,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "chunk_type": self.chunk_type,
            "preview": self.preview,
            "dense_score": self.dense_score,
            "bm25_score": self.bm25_score,
            "fusion_score": self.fusion_score,
            "metadata_bonus": self.metadata_bonus,
            "metadata_final_score": self.metadata_final_score,
            "cross_encoder_score": self.cross_encoder_score,
            "final_score": self.final_score,
            "selected_for_context": self.selected_for_context,
            "found_by_queries": list(self.found_by_queries),
            "stage": self.stage,
        }


@dataclass
class PerQueryRetrievalTrace:
    """Top-K results for one expanded retrieval query."""

    retrieval_query: str
    dense_hits: list[ChunkHitTrace] = field(default_factory=list)
    bm25_hits: list[ChunkHitTrace] = field(default_factory=list)
    fusion_hits: list[ChunkHitTrace] = field(default_factory=list)
    metadata_hits: list[ChunkHitTrace] = field(default_factory=list)


@dataclass
class ExpectedChunkVerdict:
    """Whether an expected content signature was retrieved."""

    label: str
    signature: str
    expected_chunk_id: str | None
    expected_document: str | None
    expected_page: int | None
    expected_preview: str | None
    retrieved: bool
    best_rank: int | None
    fate: str  # found_in_final | discarded_after_rerank | discarded_after_fusion | never_retrieved | unknown
    stages_seen: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "signature": self.signature,
            "expected_chunk_id": self.expected_chunk_id,
            "expected_document": self.expected_document,
            "expected_page": self.expected_page,
            "expected_preview": self.expected_preview,
            "retrieved": self.retrieved,
            "best_rank": self.best_rank,
            "fate": self.fate,
            "stages_seen": list(self.stages_seen),
        }


@dataclass
class FinalContextChunk:
    order: int
    document: str
    page: int | None
    chunk_id: str
    chunk_type: str | None
    preview: str
    found_by_queries: list[str] = field(default_factory=list)


@dataclass
class RagDiagnosticReport:
    """Complete diagnostic report for one user question."""

    question: str
    understanding: dict[str, Any] = field(default_factory=dict)
    expansion_queries: list[str] = field(default_factory=list)
    expansion_strategy: str | None = None
    per_query: list[PerQueryRetrievalTrace] = field(default_factory=list)
    post_fusion_merge: list[ChunkHitTrace] = field(default_factory=list)
    post_rerank: list[ChunkHitTrace] = field(default_factory=list)
    final_context: list[FinalContextChunk] = field(default_factory=list)
    final_context_chars: int = 0
    final_context_approx_tokens: int = 0
    expected_chunk_verdicts: list[ExpectedChunkVerdict] = field(default_factory=list)
    answer_plan: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)
    answer_composition: dict[str, Any] = field(default_factory=dict)
    answer_synthesis: dict[str, Any] = field(default_factory=dict)
    response_layout: dict[str, Any] = field(default_factory=dict)
    markdown_render: dict[str, Any] = field(default_factory=dict)
    presentation_polish: dict[str, Any] = field(default_factory=dict)
    presentation_finalize: dict[str, Any] = field(default_factory=dict)
    gaqa_report: dict[str, Any] = field(default_factory=dict)
    model_output: str | None = None
    final_answer: str | None = None
    answer_kind: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "understanding": self.understanding,
            "expansion_queries": list(self.expansion_queries),
            "expansion_strategy": self.expansion_strategy,
            "answer_plan": dict(self.answer_plan),
            "evidence_graph": dict(self.evidence_graph),
            "answer_composition": dict(self.answer_composition),
            "answer_synthesis": dict(self.answer_synthesis),
            "response_layout": dict(self.response_layout),
            "markdown_render": dict(self.markdown_render),
            "presentation_polish": dict(self.presentation_polish),
            "presentation_finalize": dict(self.presentation_finalize),
            "gaqa_report": dict(self.gaqa_report),
            "per_query": [
                {
                    "retrieval_query": item.retrieval_query,
                    "dense_hits": [h.to_dict() for h in item.dense_hits],
                    "bm25_hits": [h.to_dict() for h in item.bm25_hits],
                    "fusion_hits": [h.to_dict() for h in item.fusion_hits],
                    "metadata_hits": [h.to_dict() for h in item.metadata_hits],
                }
                for item in self.per_query
            ],
            "post_fusion_merge": [h.to_dict() for h in self.post_fusion_merge],
            "post_rerank": [h.to_dict() for h in self.post_rerank],
            "final_context": [
                {
                    "order": c.order,
                    "document": c.document,
                    "page": c.page,
                    "chunk_id": c.chunk_id,
                    "chunk_type": c.chunk_type,
                    "preview": c.preview,
                    "found_by_queries": list(c.found_by_queries),
                }
                for c in self.final_context
            ],
            "final_context_chars": self.final_context_chars,
            "final_context_approx_tokens": self.final_context_approx_tokens,
            "expected_chunk_verdicts": [v.to_dict() for v in self.expected_chunk_verdicts],
            "model_output": self.model_output,
            "final_answer": self.final_answer,
            "answer_kind": self.answer_kind,
            "errors": list(self.errors),
        }
