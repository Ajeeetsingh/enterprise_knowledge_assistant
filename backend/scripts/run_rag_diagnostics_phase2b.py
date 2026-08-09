"""Phase 2B — run RAG observability traces for the three acceptance questions.

Usage (from repo root or backend/):
    python backend/scripts/run_rag_diagnostics_phase2b.py

Does NOT change ranking, embeddings, chunking, or prompts.
Writes human-readable + JSON reports under storage/diagnostics/.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ACCEPTANCE_QUESTIONS = [
    "What is Apex National Bank's mission, vision, and core values?",
    "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
    "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
]


def main() -> int:
    from app.config import get_settings
    from app.core.logging import setup_logging
    from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
    from app.db.session import SessionLocal
    from app.documents.status import DocumentStatus
    from app.rag.observability.collector import trace_question
    from app.rag.observability.reporter import render_diagnostic_report, write_diagnostic_report
    from app.services.document_service import get_document_service
    from app.services.index_bootstrap_service import bootstrap_search_index
    from app.services.rag_service import RagService, get_rag_service

    setup_logging()
    settings = get_settings()

    document_service = get_document_service()
    with SessionLocal() as session:
        vector_count = bootstrap_search_index(session, document_service)
        repository = DocumentRepository(session)
        documents, total = repository.list(
            limit=10_000,
            offset=0,
            filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
        )
        authorized_sources = frozenset(doc.filename for doc in documents if doc.filename)

    print(f"Bootstrapped vector index size: {vector_count}")
    print(f"Searchable documents: {total}")
    print(f"Authorized sources ({len(authorized_sources)}):")
    for name in sorted(authorized_sources):
        print(f"  - {name}")

    if vector_count <= 0:
        print("ERROR: empty vector index — cannot run diagnostics.")
        return 1

    get_rag_service.cache_clear()
    # Script owns the trace lifecycle — disable RagService auto-wrap to avoid doubles.
    service = RagService(
        settings.model_copy(update={"rag_diagnostics_enabled": False})
    )
    service.initialize()

    store = document_service.vector_store
    indexed_chunks = list(getattr(store, "chunks", None) or [])
    if not indexed_chunks and hasattr(store, "_faiss"):
        indexed_chunks = list(getattr(store._faiss, "chunks", []) or [])

    report_paths: list[Path] = []
    for index, question in enumerate(ACCEPTANCE_QUESTIONS, start=1):
        print("\n" + "=" * 72)
        print(f"[{index}/{len(ACCEPTANCE_QUESTIONS)}] {question}")
        print("=" * 72)
        with trace_question(question) as session:
            response = service.answer_question(
                question,
                "admin",
                authorized_sources,
            )
            # Ensure answer is recorded even if engine path skipped a hook.
            if session.report.final_answer is None:
                session.record_final_answer(
                    response.answer,
                    answer_kind=getattr(response, "message", None),
                )
            if not session.report.expected_chunk_verdicts and indexed_chunks:
                session.evaluate_expected(indexed_chunks)
            report = session.report

        # trace_question already wrote under storage/diagnostics/; print summary.
        print(f"Answer preview: {(response.answer or '')[:240]!r}")
        print(f"Sources: {response.sources_used}")
        print(f"Confidence: {response.confidence_score}")
        if report.expected_chunk_verdicts:
            print("Expected-chunk verdicts:")
            for verdict in report.expected_chunk_verdicts:
                line = (
                    f"  - {verdict.label}: retrieved={verdict.retrieved} "
                    f"rank={verdict.best_rank} fate={verdict.fate}"
                )
                # Windows consoles may be cp1252 — keep stdout ASCII-safe.
                print(line.encode("ascii", errors="replace").decode("ascii"))

        # Also write an explicit acceptance-labeled copy for the deliverable.
        text = render_diagnostic_report(report)
        out = write_diagnostic_report(
            report,
            text,
            output_dir=settings.storage_path / "diagnostics" / "phase2b",
        )
        if out is not None:
            report_paths.append(out)
            print(f"Report: {out}")

    summary = settings.storage_path / "diagnostics" / "phase2b" / "ACCEPTANCE_SUMMARY.txt"
    summary.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Phase 2B Acceptance Diagnostic Summary",
        "=" * 52,
        "",
        "Observability only — no retrieval algorithm changes.",
        "",
    ]
    for path in report_paths:
        lines.append(f"- {path}")
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSummary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
