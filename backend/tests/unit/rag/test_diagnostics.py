"""Unit tests for retrieval diagnostics (DEBUG mode) tracing."""

from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.types import ChunkMetadata, ChunkType
from app.rag.diagnostics import explain_query, format_trace
from app.rag.hybrid.bm25 import BM25Index
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.reranking.config import RerankingSettings


class _StubVectorStore:
    """Minimal FAISS-shaped stub returning fixed dense candidates."""

    def __init__(self, chunks: list[DocumentChunk], scores: list[float]) -> None:
        self._chunks = chunks
        self._scores = scores
        self.size = len(chunks)

    def gather_candidates(self, query, *, limit, allowed_categories=None, allowed_sources=None, min_score=0.0):
        from app.ingestion.vector_store.candidates import VectorSearchCandidate

        return [
            VectorSearchCandidate(chunk=chunk, raw_cosine_score=score)
            for chunk, score in zip(self._chunks, self._scores, strict=True)
        ][:limit]


def _chunk(chunk_id: str, content: str, *, heading: str) -> DocumentChunk:
    metadata = ChunkMetadata(chunk_type=ChunkType.PARAGRAPH, section_title=heading, contains_heading=True)
    return DocumentChunk(
        chunk_id=chunk_id,
        content=content,
        source="doc.pdf",
        category="general",
        chunk_index=0,
        page_number=3,
        metadata=metadata,
    )


def test_explain_query_reports_every_stage(tmp_path) -> None:
    chunks = [
        _chunk("issuers", "Issuer body text about commercial paper.", heading="Who are the main issuers?"),
        _chunk(
            "investors", "Investor body text about commercial paper.", heading="Who are the main investors?"
        ),
    ]
    vector_store = _StubVectorStore(chunks, scores=[0.7, 0.75])
    bm25 = BM25Index(settings=HybridRetrievalSettings(), persist_path=tmp_path / "bm25.json")
    bm25.add_chunks(chunks, document_id="doc-1")

    trace = explain_query(
        "Who are the main commercial paper issuers?",
        vector_store=vector_store,
        bm25_index=bm25,
        reranking_settings=RerankingSettings(enabled=False),
        top_k=2,
    )

    assert trace.query == "Who are the main commercial paper issuers?"
    assert {entry.chunk_id for entry in trace.dense_top_k} == {"issuers", "investors"}
    assert {entry.chunk_id for entry in trace.bm25_top_k} == {"issuers", "investors"}
    assert all(entry.heading for entry in trace.dense_top_k)
    assert all(entry.document == "doc.pdf" for entry in trace.hybrid_merge)
    assert trace.final_context

    report = format_trace(trace)
    assert "BM25 Top K" in report
    assert "Dense Top K" in report
    assert "Hybrid Merge" in report
    assert "Reranker Top K" in report
    assert "Final Context" in report
    assert "heading=" in report
