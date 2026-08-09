"""Phase 3A regression: re-index Company Profile and verify Mission/Vision searchable."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _safe(s: object) -> str:
    return str(s).encode("ascii", "replace").decode("ascii")


def main() -> int:
    from app.db.session import SessionLocal
    from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
    from app.documents.status import DocumentStatus
    from app.services.document_service import get_document_service, get_document_service as _
    from app.services.index_bootstrap_service import bootstrap_search_index
    from app.rag.hybrid.retriever import HybridRetriever
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.hybrid.index_store import HybridIndexStore

    service = get_document_service()
    with SessionLocal() as session:
        repo = DocumentRepository(session)
        docs, _total = repo.list(
            limit=100,
            offset=0,
            filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
        )
        doc = next(
            (
                d
                for d in docs
                if "COMPANY_PROFILE" in (d.filename or "").upper().replace(" ", "_")
            ),
            None,
        )
        if doc is None:
            print("ERROR: COMPANY_PROFILE not found")
            return 1

        filename = doc.filename
        doc_id = str(doc.id)
        print("Re-indexing", filename, doc_id)
        content = service.storage.resolve(doc.storage_path).read_bytes()
        service.reindex_document_vectors(
            document_id=doc_id,
            filename=filename,
            content_type=doc.content_type or "application/pdf",
            content=content,
        )

    store = service.vector_store
    faiss: FaissVectorStore
    bm25 = None
    if isinstance(store, HybridIndexStore):
        faiss = store.faiss_store
        bm25 = store.bm25_index
    else:
        faiss = store  # type: ignore[assignment]

    # Chunk inventory around Mission/Vision
    print("\n=== INDEXED CHUNKS containing Mission/Vision/Core ===")
    found_mission = found_vision = found_values = False
    for chunk in faiss.chunks:
        if chunk.source != filename and filename not in chunk.source:
            # source may be bare filename
            if "COMPANY_PROFILE" not in (chunk.source or "").upper():
                continue
        text = chunk.content or ""
        hit = False
        if "To steward our clients" in text or "1.4 Mission" in text:
            found_mission = True
            hit = True
        if "most trusted and operationally resilient" in text or "1.5 Vision" in text:
            found_vision = True
            hit = True
        if "1.6 Core Values" in text or "Client Stewardship" in text:
            found_values = True
            hit = True
        if hit:
            print(
                _safe(
                    f"id={chunk.chunk_id} page={chunk.page_number} chars={len(text)}"
                )
            )
            print(_safe(text[:300].replace("\n", " | ")))
            print("---")

    print("\nMission body indexed:", found_mission)
    print("Vision body indexed:", found_vision)
    print("Core Values indexed:", found_values)

    # BM25 membership
    if bm25 is not None:
        ids = set(getattr(bm25, "_chunk_ids", []) or [])
        print("\nBM25 size", bm25.size)
        mission_ids = [
            c.chunk_id
            for c in faiss.chunks
            if "To steward our clients" in (c.content or "")
        ]
        vision_ids = [
            c.chunk_id
            for c in faiss.chunks
            if "most trusted and operationally resilient" in (c.content or "")
        ]
        print("Mission chunk ids in BM25:", [(i, i in ids) for i in mission_ids])
        print("Vision chunk ids in BM25:", [(i, i in ids) for i in vision_ids])

    # Hybrid search smoke (pre-rerank path)
    print("\n=== SEARCH RESULTS ===")
    retriever = HybridRetriever()
    queries = [
        "mission",
        "vision",
        "mission statement",
        "core values",
        "company mission",
        "company vision",
        "To steward our clients",
        "most trusted and operationally resilient",
    ]
    if bm25 is None:
        print("No BM25 — dense-only skip hybrid")
        return 1 if not (found_mission and found_vision and found_values) else 0

    for query in queries:
        results = retriever.search(
            faiss,
            bm25,
            query,
            top_k=8,
            allowed_sources={filename},
        )
        print(f"\nQUERY: {query!r} -> {len(results)} hits")
        for rank, item in enumerate(results[:5], start=1):
            preview = (item.content or "")[:120].replace("\n", " ")
            print(
                _safe(
                    f"  #{rank} p{item.page_number} {item.chunk_id} "
                    f"score={item.confidence:.4f}"
                )
            )
            print(_safe(f"     {preview}"))

    ok = found_mission and found_vision and found_values
    print("\nREGRESSION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
