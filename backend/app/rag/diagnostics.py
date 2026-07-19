"""Retrieval diagnostics — stage-by-stage tracing for debugging ranking issues.

Runs the same building blocks used by :class:`HybridRetriever` and
:class:`CrossEncoderReranker` independently so every stage — BM25, dense,
hybrid merge, reranking, final context — can be inspected side by side for
a single query. This is read-only and additive: it does not change
``HybridRetriever``/``EnterpriseRAG`` behaviour, return types, or the
public API — it is a separate, opt-in tool for debugging retrieval
quality (see ``app.rag.cli`` for a command-line entry point and
``tests/unit/rag/test_diagnostics.py`` for usage).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.rag.hybrid.bm25 import BM25Index
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.hybrid.dense import DenseRetriever
from app.rag.hybrid.fusion import FusionEngine
from app.rag.hybrid.sparse import SparseRetriever
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.metadata_retrieval.intent import detect_query_intent
from app.rag.metadata_retrieval.retriever import MetadataAwareRetriever
from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.reranker import CrossEncoderReranker
from app.rag.types import RetrievalResult


@dataclass(frozen=True)
class DiagnosticEntry:
    """A single chunk's trace entry at one retrieval stage."""

    rank: int
    chunk_id: str
    document: str
    page: int | None
    heading: str | None
    score: float | None
    source: str  # "dense" | "bm25" | "both" | "unknown"


@dataclass(frozen=True)
class RetrievalDebugTrace:
    """Full stage-by-stage trace for a single query."""

    query: str
    bm25_top_k: list[DiagnosticEntry]
    dense_top_k: list[DiagnosticEntry]
    hybrid_merge: list[DiagnosticEntry]
    reranker_top_k: list[DiagnosticEntry]
    final_context: list[DiagnosticEntry]

    def render(self) -> str:
        return format_trace(self)


def _entry_from_dense_hit(hit, *, rank: int) -> DiagnosticEntry:
    chunk = hit.chunk
    metadata = getattr(chunk, "metadata", None)
    return DiagnosticEntry(
        rank=rank,
        chunk_id=chunk.chunk_id,
        document=chunk.source,
        page=chunk.page_number,
        heading=getattr(metadata, "section_title", None),
        score=round(hit.raw_cosine_score, 4),
        source="dense",
    )


def _entry_from_sparse_hit(hit, *, rank: int) -> DiagnosticEntry:
    chunk = hit.chunk
    metadata = getattr(chunk, "metadata", None)
    return DiagnosticEntry(
        rank=rank,
        chunk_id=chunk.chunk_id,
        document=chunk.source,
        page=chunk.page_number,
        heading=getattr(metadata, "section_title", None),
        score=round(hit.bm25_score, 4),
        source="bm25",
    )


def _source_label(result: RetrievalResult) -> str:
    sources = result.source_retrievers or []
    if len(sources) >= 2:
        return "both"
    if sources:
        return sources[0]
    return "unknown"


def _entry_from_result(
    result: RetrievalResult,
    *,
    rank: int,
    score_field: str,
) -> DiagnosticEntry:
    score = getattr(result, score_field, None)
    return DiagnosticEntry(
        rank=rank,
        chunk_id=result.chunk_id,
        document=result.source,
        page=result.page_number,
        heading=result.section_title,
        score=round(score, 4) if score is not None else None,
        source=_source_label(result),
    )


def explain_query(
    query: str,
    *,
    vector_store: FaissVectorStore,
    bm25_index: BM25Index,
    hybrid_settings: HybridRetrievalSettings | None = None,
    metadata_settings: MetadataRetrievalSettings | None = None,
    reranking_settings: RerankingSettings | None = None,
    top_k: int = 5,
    allowed_categories: set[str] | None = None,
    allowed_sources: set[str] | None = None,
) -> RetrievalDebugTrace:
    """Run every retrieval stage independently and return a full trace.

    Mirrors ``HybridRetriever.search()`` + ``CrossEncoderReranker.rerank()``
    step by step, but keeps each stage's output separately visible instead
    of only returning the final ranked list.
    """
    hybrid_settings = hybrid_settings or HybridRetrievalSettings.from_settings()
    metadata_settings = metadata_settings or MetadataRetrievalSettings.from_settings()
    reranking_settings = reranking_settings or RerankingSettings.from_settings()

    dense = DenseRetriever()
    sparse = SparseRetriever()
    fusion = FusionEngine()
    metadata_retriever = MetadataAwareRetriever(settings=metadata_settings)
    reranker = CrossEncoderReranker(
        settings=reranking_settings,
        metadata_bonus_reference=metadata_settings.max_metadata_bonus,
    )

    intent = detect_query_intent(query)

    dense_hits, _ = dense.gather(
        vector_store,
        query,
        limit=hybrid_settings.top_k_dense,
        allowed_categories=allowed_categories,
        allowed_sources=allowed_sources,
    )
    sparse_hits, _ = sparse.gather(
        bm25_index,
        query,
        limit=hybrid_settings.top_k_sparse,
        allowed_categories=allowed_categories,
        allowed_sources=allowed_sources,
    )
    fused, _fusion_stats = fusion.fuse(
        dense_hits=dense_hits,
        sparse_hits=sparse_hits,
        settings=hybrid_settings,
        intent=intent,
    )

    fetch_k = max(hybrid_settings.top_k_dense, hybrid_settings.top_k_sparse)
    candidates = [
        VectorSearchCandidate(
            chunk=item.chunk,
            raw_cosine_score=item.raw_cosine_score,
            bm25_score=item.bm25_score,
            dense_rank=item.dense_rank,
            sparse_rank=item.sparse_rank,
            fusion_score=item.fusion_score,
            fusion_explanation=list(item.fusion_explanation),
            source_retrievers=list(item.source_retrievers),
        )
        for item in fused[:fetch_k]
    ]

    hybrid_merged = metadata_retriever.rescore_candidates(query, candidates, top_k=fetch_k)
    reranked = reranker.rerank(query, hybrid_merged, top_k=top_k)

    return RetrievalDebugTrace(
        query=query,
        bm25_top_k=[
            _entry_from_sparse_hit(hit, rank=idx + 1) for idx, hit in enumerate(sparse_hits)
        ],
        dense_top_k=[
            _entry_from_dense_hit(hit, rank=idx + 1) for idx, hit in enumerate(dense_hits)
        ],
        hybrid_merge=[
            _entry_from_result(result, rank=idx + 1, score_field="final_score")
            for idx, result in enumerate(hybrid_merged)
        ],
        reranker_top_k=[
            _entry_from_result(result, rank=idx + 1, score_field="reranker_score")
            for idx, result in enumerate(reranked)
        ],
        final_context=[
            _entry_from_result(result, rank=idx + 1, score_field="final_score")
            for idx, result in enumerate(reranked[:top_k])
        ],
    )


def format_trace(trace: RetrievalDebugTrace) -> str:
    """Render a trace as a readable text report for logs/CLI."""
    lines = [f"Query: {trace.query}"]

    def _section(title: str, entries: list[DiagnosticEntry]) -> None:
        lines.append(f"\n{title}")
        if not entries:
            lines.append("  (empty)")
            return
        for entry in entries:
            lines.append(
                f"  #{entry.rank:<2} doc={entry.document} page={entry.page} "
                f"heading={entry.heading!r} score={entry.score} "
                f"source={entry.source} chunk_id={entry.chunk_id}"
            )

    _section("BM25 Top K", trace.bm25_top_k)
    _section("Dense Top K", trace.dense_top_k)
    _section("Hybrid Merge", trace.hybrid_merge)
    _section("Reranker Top K", trace.reranker_top_k)
    _section("Final Context", trace.final_context)
    return "\n".join(lines)
