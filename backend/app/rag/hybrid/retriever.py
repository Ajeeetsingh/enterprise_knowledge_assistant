"""Hybrid dense + sparse retrieval orchestrator."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.hybrid.dense import DenseRetriever
from app.rag.hybrid.fusion import FusionEngine
from app.rag.hybrid.metrics import log_hybrid_retrieval
from app.rag.hybrid.schemas import HybridRetrievalMetrics
from app.rag.hybrid.sparse import SparseRetriever
from app.rag.metadata_retrieval.intent import detect_query_intent
from app.rag.metadata_retrieval.retriever import MetadataAwareRetriever
from app.rag.types import RetrievalResult

if TYPE_CHECKING:
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.hybrid.bm25 import BM25Index

logger = get_logger(__name__)


class HybridRetriever:
    """Production hybrid retrieval pipeline."""

    def __init__(
        self,
        *,
        settings: HybridRetrievalSettings | None = None,
        metadata_retriever: MetadataAwareRetriever | None = None,
        dense_retriever: DenseRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        fusion_engine: FusionEngine | None = None,
    ) -> None:
        self._settings = settings or HybridRetrievalSettings.from_settings()
        self._metadata_retriever = metadata_retriever or MetadataAwareRetriever()
        self._dense = dense_retriever or DenseRetriever()
        self._sparse = sparse_retriever or SparseRetriever()
        self._fusion = fusion_engine or FusionEngine()

    @property
    def settings(self) -> HybridRetrievalSettings:
        return self._settings

    def ensure_bm25_synced(
        self,
        vector_store: FaissVectorStore,
        bm25_index: BM25Index,
    ) -> None:
        """Rebuild BM25 from FAISS chunks when indexes diverge (evaluation bootstrap)."""
        if bm25_index.size == vector_store.size:
            return
        bm25_index.rebuild_from_chunks(
            vector_store.chunks,
            chunk_ids=[chunk.chunk_id for chunk in vector_store.chunks],
            document_ids=getattr(vector_store, "_document_ids", None),
        )

    def search(
        self,
        vector_store: FaissVectorStore,
        bm25_index: BM25Index,
        query: str,
        *,
        top_k: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        started = time.perf_counter()
        settings = self._settings
        self.ensure_bm25_synced(vector_store, bm25_index)

        intent = detect_query_intent(query)
        dense_hits, dense_latency = self._dense.gather(
            vector_store,
            query,
            limit=settings.top_k_dense,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
            min_score=min_score,
        )
        sparse_hits, sparse_latency = self._sparse.gather(
            bm25_index,
            query,
            limit=settings.top_k_sparse,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
        )

        fusion_started = time.perf_counter()
        fused, fusion_stats = self._fusion.fuse(
            dense_hits=dense_hits,
            sparse_hits=sparse_hits,
            settings=settings,
            intent=intent,
        )
        fusion_latency = round((time.perf_counter() - fusion_started) * 1000, 3)

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
            for item in fused[: max(settings.top_k_dense, settings.top_k_sparse)]
        ]

        metadata_started = time.perf_counter()
        final_k = top_k or settings.top_k_final
        results = self._metadata_retriever.rescore_candidates(
            query,
            candidates,
            top_k=final_k,
        )
        metadata_latency = round((time.perf_counter() - metadata_started) * 1000, 3)

        metrics = HybridRetrievalMetrics(
            dense_latency_ms=dense_latency,
            sparse_latency_ms=sparse_latency,
            fusion_latency_ms=fusion_latency,
            metadata_latency_ms=metadata_latency,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
            dense_candidate_count=len(dense_hits),
            sparse_candidate_count=len(sparse_hits),
            fused_candidate_count=len(fused),
            dense_only_count=int(fusion_stats.get("dense_only", 0)),
            sparse_only_count=int(fusion_stats.get("sparse_only", 0)),
            both_count=int(fusion_stats.get("both", 0)),
            fusion_statistics=fusion_stats,
        )
        log_hybrid_retrieval(
            query=query,
            metrics=metrics,
            top_fusion_scores=[item.fusion_score for item in fused[:final_k]],
        )
        return results
