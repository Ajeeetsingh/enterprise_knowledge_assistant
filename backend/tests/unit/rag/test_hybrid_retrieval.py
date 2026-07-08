"""Unit tests for hybrid dense + sparse retrieval."""

from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.rag.hybrid.bm25 import BM25Index
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.hybrid.fusion import FusionEngine, resolve_fusion_weights
from app.rag.hybrid.index_store import HybridIndexStore
from app.rag.hybrid.schemas import DenseSearchHit, SparseSearchHit
from app.rag.metadata_retrieval.intent import IntentDetectionResult, QueryIntent


def _chunk(chunk_id: str, content: str, *, source: str = "doc.pdf") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        content=content,
        source=source,
        category="general",
        chunk_index=0,
        page_number=1,
    )


def _settings(**overrides) -> HybridRetrievalSettings:
    defaults = {
        "enabled": True,
        "sparse_weight": 1.0,
        "dense_weight": 1.0,
        "rrf_k": 60,
        "bm25_k1": 1.5,
        "bm25_b": 0.75,
        "top_k_dense": 5,
        "top_k_sparse": 5,
        "top_k_final": 3,
    }
    defaults.update(overrides)
    return HybridRetrievalSettings(**defaults)


def test_bm25_index_incremental_update_and_delete(tmp_path) -> None:
    index = BM25Index(settings=_settings(), persist_path=tmp_path / "bm25.json")
    chunks = [
        _chunk("a", "Singapore headquarters for GlobalTrust Financial Services"),
        _chunk("b", "Quarterly revenue increased to 4.5 billion dollars"),
    ]
    index.add_chunks(chunks, document_id="doc-1")
    assert index.size == 2

    hits = index.search("Singapore headquarters", limit=1)
    assert hits
    assert hits[0].chunk.chunk_id == "a"

    index.remove_document("doc-1")
    assert index.size == 0


def test_bm25_rebuild_from_chunks(tmp_path) -> None:
    index = BM25Index(settings=_settings(), persist_path=tmp_path / "bm25.json")
    chunks = [_chunk("x", "David Chen is the Chief Executive Officer")]
    index.rebuild_from_chunks(chunks)
    hits = index.search("David Chen CEO", limit=1)
    assert hits[0].chunk.chunk_id == "x"


def test_fusion_rrf_prefers_chunks_in_both_lists() -> None:
    settings = _settings(rrf_k=60)
    engine = FusionEngine()
    dense = [
        DenseSearchHit(chunk=_chunk("a", "alpha"), raw_cosine_score=0.8, rank=3),
        DenseSearchHit(chunk=_chunk("b", "beta"), raw_cosine_score=0.7, rank=1),
    ]
    sparse = [
        SparseSearchHit(chunk=_chunk("a", "alpha"), bm25_score=4.2, rank=1),
        SparseSearchHit(chunk=_chunk("c", "gamma"), bm25_score=3.1, rank=2),
    ]
    fused, stats = engine.fuse(
        dense_hits=dense,
        sparse_hits=sparse,
        settings=settings,
        intent=IntentDetectionResult(QueryIntent.GENERAL, ()),
    )
    assert fused[0].chunk.chunk_id == "a"
    assert stats["both"] == 1.0
    assert "dense" in fused[0].source_retrievers
    assert "sparse" in fused[0].source_retrievers


def test_fusion_tie_break_is_deterministic() -> None:
    settings = _settings(rrf_k=60)
    engine = FusionEngine()
    dense = [DenseSearchHit(chunk=_chunk("b", "beta"), raw_cosine_score=0.5, rank=1)]
    sparse = [SparseSearchHit(chunk=_chunk("a", "alpha"), bm25_score=2.0, rank=1)]
    intent = IntentDetectionResult(QueryIntent.GENERAL, ())

    first, _ = engine.fuse(
        dense_hits=dense,
        sparse_hits=sparse,
        settings=settings,
        intent=intent,
    )
    second, _ = engine.fuse(
        dense_hits=dense,
        sparse_hits=sparse,
        settings=settings,
        intent=intent,
    )
    assert [item.chunk.chunk_id for item in first] == [item.chunk.chunk_id for item in second]


def test_intent_routing_favors_sparse_for_numeric_queries() -> None:
    settings = _settings()
    dense_weight, sparse_weight = resolve_fusion_weights(
        IntentDetectionResult(QueryIntent.NUMERIC_INTENT, ("numeric_keyword",)),
        settings,
    )
    assert sparse_weight > dense_weight


def test_hybrid_index_store_keeps_faiss_and_bm25_in_sync(tmp_path) -> None:
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from unittest.mock import MagicMock

    faiss = MagicMock(spec=FaissVectorStore)
    faiss.add_chunks.return_value = ["a"]
    faiss.size = 1
    bm25 = BM25Index(settings=_settings(), persist_path=tmp_path / "bm25.json")
    store = HybridIndexStore(faiss, bm25)
    chunk = _chunk("a", "password policy requires MFA")
    store.add_chunks([chunk], [[0.1, 0.2, 0.3]], document_id="doc-1")
    assert bm25.size == 1
    faiss.remove_document.assert_not_called()
    store.remove_document("doc-1")
    assert bm25.size == 0
    faiss.remove_document.assert_called_once_with("doc-1")
