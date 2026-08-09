"""Phase 3B ranking diagnostics for metadata + BPC questions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


QUESTIONS = [
    "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
    "Explain how the Business Process Classification Guide connects processes, documents, risks, systems, business entities, and compliance requirements.",
    "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
]


def _safe(s: object) -> str:
    return str(s).encode("ascii", "replace").decode("ascii")


def main() -> int:
    from app.db.session import SessionLocal
    from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
    from app.documents.status import DocumentStatus
    from app.services.document_service import get_document_service
    from app.services.index_bootstrap_service import bootstrap_search_index
    from app.services.rag_service import RagService
    from app.config import get_settings
    from app.rag.observability.collector import trace_question
    from app.rag.observability.reporter import render_diagnostic_report, write_diagnostic_report
    from app.core.logging import setup_logging

    setup_logging()
    settings = get_settings()
    doc_service = get_document_service()
    with SessionLocal() as session:
        bootstrap_search_index(session, doc_service)
        docs, _ = DocumentRepository(session).list(
            limit=10_000,
            offset=0,
            filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
        )
        sources = frozenset(d.filename for d in docs if d.filename)

    print("sources", len(sources), "vector", doc_service.vector_store.size)
    print("rerank_top_n", getattr(settings, "rerank_top_n", None))
    print("top_k_final", getattr(settings, "top_k_final", None))

    service = RagService(settings.model_copy(update={"rag_diagnostics_enabled": False}))
    service.initialize()

    out_dir = settings.storage_path / "diagnostics" / "phase3b"
    out_dir.mkdir(parents=True, exist_ok=True)

    for q in QUESTIONS:
        print("\n" + "=" * 72)
        print(_safe(q))
        with trace_question(q) as session:
            resp = service.answer_question(q, "admin", sources)
            report = session.report
            if not report.expected_chunk_verdicts:
                store = doc_service.vector_store
                chunks = list(getattr(store, "chunks", None) or [])
                if not chunks and hasattr(store, "_faiss"):
                    chunks = list(store._faiss.chunks)
                session.evaluate_expected(chunks)

        text = render_diagnostic_report(report)
        path = write_diagnostic_report(report, text, output_dir=out_dir)
        print("answer:", _safe((resp.answer or "")[:300]))
        print("sources:", resp.sources_used)
        print("report:", path)

        # Ranking analysis
        merge = report.post_fusion_merge or []
        rerank = report.post_rerank or []
        final_ids = {c.chunk_id for c in report.final_context}
        print(f"merge_n={len(merge)} rerank_n={len(rerank)} final_n={len(report.final_context)}")
        print("TOP5 MERGE:")
        for h in merge[:5]:
            print(
                _safe(
                    f"  #{h.rank} p{h.page} fusion={h.fusion_score} meta={h.metadata_bonus} "
                    f"final={h.metadata_final_score or h.final_score} bm25={h.bm25_score} "
                    f"dense={h.dense_score} {h.filename}"
                )
            )
            print(_safe(f"     {(h.preview or '')[:120]}"))
        print("TOP/ALL RERANK:")
        for h in rerank:
            mark = "F" if h.chunk_id in final_ids else " "
            print(
                _safe(
                    f" {mark}#{h.rank} p{h.page} ce={h.cross_encoder_score} "
                    f"final={h.final_score} meta={h.metadata_bonus} {h.filename} "
                    f"{h.chunk_id.split('::')[-1]}"
                )
            )
            print(_safe(f"     {(h.preview or '')[:120]}"))
        print("VERDICTS:")
        for v in report.expected_chunk_verdicts:
            print(
                _safe(
                    f"  {v.label}: retrieved={v.retrieved} rank={v.best_rank} "
                    f"fate={v.fate} id={v.expected_chunk_id}"
                )
            )
            # locate in merge/rerank
            eid = v.expected_chunk_id
            if eid:
                for h in merge:
                    if h.chunk_id == eid:
                        print(
                            _safe(
                                f"    MERGE #{h.rank} fusion={h.fusion_score} "
                                f"meta={h.metadata_bonus} final={h.metadata_final_score or h.final_score} "
                                f"dense={h.dense_score} bm25={h.bm25_score}"
                            )
                        )
                for h in rerank:
                    if h.chunk_id == eid:
                        print(
                            _safe(
                                f"    RERANK #{h.rank} ce={h.cross_encoder_score} "
                                f"final={h.final_score} selected={h.selected_for_context}"
                            )
                        )
                if eid not in {h.chunk_id for h in rerank} and eid in {
                    h.chunk_id for h in merge
                }:
                    print("    NOT IN RERANK POOL (truncated before CrossEncoder)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
