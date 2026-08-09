"""Phase 3A forensic: Company Profile extraction + chunking around Mission/Vision."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _safe(s: str) -> str:
    return (s or "").encode("ascii", "replace").decode("ascii")


def find_company_profile() -> tuple[str, str, bytes]:
    from app.db.session import SessionLocal
    from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
    from app.documents.status import DocumentStatus
    from app.services.document_service import get_document_service

    service = get_document_service()
    with SessionLocal() as session:
        repo = DocumentRepository(session)
        docs, _ = repo.list(
            limit=100,
            offset=0,
            filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
        )
        for doc in docs:
            name = (doc.filename or "").upper()
            if "COMPANY_PROFILE" in name.replace(" ", "_") or "COMPANY PROFILE" in name:
                content = service.storage.resolve(doc.storage_path).read_bytes()
                return doc.filename, str(doc.id), content
            if "COMPANY" in name and "PROFILE" in name:
                content = service.storage.resolve(doc.storage_path).read_bytes()
                return doc.filename, str(doc.id), content
    raise SystemExit("COMPANY_PROFILE document not found in DB")


def main() -> None:
    from app.documents.types import IngestionContext
    from app.ingestion.parsers.pdf import PdfParser
    from app.ingestion.processor import DefaultDocumentProcessor
    from app.ingestion.structure.extractor import StructureExtractor
    from app.ingestion.structure.models import BlockType
    from app.ingestion.semantic_chunking.engine import SemanticChunkEngine

    filename, doc_id, pdf_bytes = find_company_profile()
    print("FILE", filename)
    print("DOC_ID", doc_id)
    print("BYTES", len(pdf_bytes))

    parser = PdfParser()
    raw = parser.parse(pdf_bytes, filename)

    print("\n=== RAW PARSER pages with Mission/Vision/Core/History ===")
    for page_marker in raw.split("<<<PAGE:"):
        if not page_marker.strip():
            continue
        num_s, _, body = page_marker.partition(">>>")
        try:
            page_num = int(num_s)
        except ValueError:
            continue
        keys = ("Mission", "Vision", "Core Values", "1.4", "1.5", "1.6", "1.3 History", "History")
        if any(k in body for k in keys) and page_num <= 15:
            print(f"\n--- RAW PAGE {page_num} chars={len(body)} ---")
            print(_safe(body[:3000]))

    context = IngestionContext(
        document_id=doc_id,
        filename=filename,
        content_type="application/pdf",
        content=pdf_bytes,
    )
    processor = DefaultDocumentProcessor()
    extracted = processor.process(context)
    print("\n=== NORMALIZED length", len(extracted))
    for label in ("1.4 Mission", "1.5 Vision", "1.6 Core Values", "1.3 History"):
        idx = extracted.lower().find(label.lower())
        print(f"\n{label}: found_at={idx} count={extracted.lower().count(label.lower())}")
        if idx >= 0:
            window = extracted[max(0, idx - 100) : idx + 800]
            print(_safe(window))

    # Also search body phrases that might appear without heading number
    for phrase in (
        "Apex National Bank exists",
        "Our mission",
        "Our vision",
        "Integrity First",
        "Client Stewardship",
        "trusted",
    ):
        idx = extracted.lower().find(phrase.lower())
        print(f"phrase[{phrase!r}] at {idx}")

    structured, issues = StructureExtractor().extract_with_validation(extracted, filename)
    print("\nstructure issues", issues[:10] if issues else None)
    print("blocks", len(structured.blocks), "headings", structured.stats.headings_detected)

    print("\n=== BLOCK SEQUENCE around History/Mission/Vision/Core ===")
    for i, block in enumerate(structured.blocks):
        text = block.text or ""
        if any(
            x in text
            for x in (
                "1.3",
                "1.4",
                "1.5",
                "1.6",
                "1.7",
                "History",
                "Mission",
                "Vision",
                "Core Values",
                "Period Milestone",
                "Client Stewardship",
            )
        ):
            # Limit noise from TOC-only far pages
            if block.page_number and block.page_number > 20 and "1.6 Core Values" not in text[:40]:
                if not any(x in text[:80] for x in ("1.4", "1.5", "1.3", "1.6", "1.7")):
                    continue
            print(
                f"[{i}] {block.block_type.value} p{block.page_number} "
                f"chars={len(text)} {_safe(text[:180].replace(chr(10), ' | '))}"
            )

    print("\n=== CONSECUTIVE HEADING DROP SIMULATION ===")
    awaiting = False
    current_heading = None
    dropped: list[str] = []
    for block in structured.blocks:
        if block.block_type == BlockType.HEADING:
            if awaiting and current_heading is not None:
                dropped.append(current_heading)
            current_heading = block.text or ""
            awaiting = True
        elif awaiting:
            awaiting = False
            current_heading = None
    for t in dropped:
        print(" DROPPED:", _safe(t[:200]))

    engine = SemanticChunkEngine()
    chunks, stats = engine.chunk_document_with_stats(
        structured, source=filename, category="general"
    )
    print("\n=== CHUNK STATS", stats)
    print("\n=== CHUNKS pages 7-11 and Mission/Vision mentions ===")
    for ch in chunks:
        text = ch.content or ""
        page = ch.page_number
        if page in (7, 8, 9, 10, 11) or any(
            k in text for k in ("1.4 Mission", "1.5 Vision", "1.6 Core", "1.3 History")
        ):
            meta = ch.metadata
            ctype = getattr(meta, "chunk_type", None) if meta else None
            print(
                f"id={ch.chunk_id} page={page} chars={len(text)} "
                f"tokens~={len(text)//4} type={ctype}"
            )
            print(" HEAD:", _safe(text[:300].replace("\n", " | ")))
            print(" TAIL:", _safe(text[-300:].replace("\n", " | ")))
            print()


if __name__ == "__main__":
    main()
