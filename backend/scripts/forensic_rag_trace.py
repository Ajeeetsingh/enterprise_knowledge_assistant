"""Read-only forensic trace of GTFS-EXEC-001 through the RAG pipeline.

Usage: python scripts/forensic_rag_trace.py
Does NOT modify any application code.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

PDF_PATHS = [
    BACKEND.parent / "data" / "GTFS-EXEC-001_Company_Overview.pdf",
    BACKEND / "storage" / "documents" / "GTFS-EXEC-001_Company_Overview.pdf",
]
FILENAME = "GTFS-EXEC-001_Company_Overview.pdf"
QUERY = "What is the company headquarters?"
TARGET_PAGE = 8


def find_pdf() -> Path:
    for path in PDF_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("GTFS-EXEC-001_Company_Overview.pdf not found")


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def extract_page_raw(pdf_bytes: bytes, page_num: int) -> str:
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    page = reader.pages[page_num - 1]
    return page.extract_text() or ""


def main() -> None:
    from app.ingestion.chunker import PAGE_MARKER_PATTERN, chunk_text
    from app.ingestion.parsers.pdf import PdfParser
    from app.ingestion.processor import DefaultDocumentProcessor
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.answer_generator import AnswerGenerator, _synthesize_structured_answer
    from app.rag.engine import EnterpriseRAG
    from app.rag.types import calibrate_confidence

    pdf_path = find_pdf()
    pdf_bytes = pdf_path.read_bytes()

    # STEP 1
    section("STEP 1 — Source document (Page 8)")
    print(f"PDF path: {pdf_path}")
    page8_raw = extract_page_raw(pdf_bytes, TARGET_PAGE)
    print(f"\n--- Page {TARGET_PAGE} raw pypdf extraction (per-page, no markers) ---")
    print(page8_raw)
    has_table_headers = "Office" in page8_raw and "Jurisdiction" in page8_raw
    has_hq = "Singapore (HQ)" in page8_raw or "Singapore(HQ)" in page8_raw.replace(" ", "")
    print(f"\nContains table column headers (Office/Country/Jurisdiction): {has_table_headers}")
    print(f"Contains 'Singapore (HQ)': {has_hq}")
    print("PDF parser flattens tables: YES — pypdf emits space-separated cells on one line")

    # STEP 2
    section("STEP 2 — Raw extraction (full document, parser output)")
    parser = PdfParser()
    raw_extracted = parser.parse(pdf_bytes, FILENAME)
    marker = f"<<<PAGE:{TARGET_PAGE}>>>"
    idx = raw_extracted.find(marker)
    if idx >= 0:
        next_marker = re.search(r"<<<PAGE:\d+>>>", raw_extracted[idx + len(marker) :])
        end = idx + len(marker) + next_marker.start() if next_marker else len(raw_extracted)
        page8_from_full = raw_extracted[idx:end]
    else:
        page8_from_full = "(page marker not found)"
    print(f"\n--- Full parser output for page {TARGET_PAGE} block ---")
    print(page8_from_full)

    # STEP 3
    section("STEP 3 — Preprocessing")
    normalized = DefaultDocumentProcessor.normalize_text(raw_extracted)
    if idx >= 0:
        nidx = normalized.find(marker)
        next_marker = re.search(r"<<<PAGE:\d+>>>", normalized[nidx + len(marker) :])
        nend = nidx + len(marker) + next_marker.start() if next_marker else len(normalized)
        page8_normalized = normalized[nidx:nend]
    else:
        page8_normalized = "(page marker not found)"

    print("\n--- Transformation 1: strip + line-ending normalize ---")
    print("(Applied inside _normalize: strip, \\r\\n -> \\n)")

    print("\n--- Transformation 2: per-line whitespace collapse ---")
    print("Each non-marker line: ' '.join(line.split()) — preserves \\n between lines")

    print("\n--- Transformation 3: collapse 3+ blank lines to 2 ---")
    print("re.sub(r'\\n{3,}', '\\n\\n', text)")

    print("\n--- Page 8 AFTER preprocessing (before chunking) ---")
    print(page8_normalized)

    geo_match = re.search(
        r".{0,120}Office.{0,200}Singapore.{0,300}",
        page8_normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if geo_match:
        print("\n--- Geographic/office table region (snippet) ---")
        print(geo_match.group(0))

    # STEP 4
    section("STEP 4 — Chunking (all chunks from page 8)")
    all_chunks = chunk_text(normalized, FILENAME, "general")
    page8_chunks = [c for c in all_chunks if c.page_number == TARGET_PAGE]
    print(f"Total document chunks: {len(all_chunks)}")
    print(f"Chunks with page_number={TARGET_PAGE}: {len(page8_chunks)}")

    for chunk in page8_chunks:
        print(f"\n--- Chunk ID: {chunk.chunk_id} ---")
        print(f"page_number: {chunk.page_number}")
        print(f"character_count: {len(chunk.content)}")
        print(f"chunk_index: {chunk.chunk_index}")
        print("FULL CHUNK TEXT:")
        print(chunk.content)
        print("-" * 40)

    # Build index
    store = FaissVectorStore()
    model = store._embedding_manager.get_model()
    import faiss
    import numpy as np

    emb = model.encode(
        [c.content for c in all_chunks],
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")
    faiss.normalize_L2(emb)
    store.add_chunks(all_chunks, [emb[i].tolist() for i in range(len(all_chunks))])

    # STEP 5
    section("STEP 5 — FAISS storage verification")
    print("Comparing chunker output vs FAISS stored chunks...")
    mismatches = 0
    for i, chunk in enumerate(all_chunks):
        stored = store._chunks[i]
        if stored.content != chunk.content:
            mismatches += 1
            print(f"MISMATCH at index {i}: {chunk.chunk_id}")
    print(f"Content mismatches: {mismatches} / {len(all_chunks)}")
    print("FAISS stores chunk text verbatim in _chunks[]; embedding is separate vector.")

    # STEP 6
    section(f'STEP 6 — Retrieval for: "{QUERY}"')
    fetch_k = 10
    query_vector = store._encode_query(QUERY)
    search_k = min(len(store._chunks), max(fetch_k * 15, fetch_k))
    scores, indices = store._index.search(query_vector, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0], strict=True):
        if idx < 0:
            continue
        chunk = store._chunks[idx]
        raw_conf = float(max(0.0, min(1.0, score)))
        results.append((raw_conf, calibrate_confidence(raw_conf), chunk, idx))
        if len(results) >= fetch_k:
            break

    for rank, (raw_conf, cal_conf, chunk, faiss_idx) in enumerate(results, 1):
        print(f"\n--- Rank {rank} ---")
        print(f"raw_cosine_similarity: {raw_conf:.6f}")
        print(f"calibrated_confidence: {cal_conf}")
        print(f"chunk_id: {chunk.chunk_id}")
        print(f"page_number: {chunk.page_number}")
        print(f"source: {chunk.source}")
        print(f"faiss_index: {faiss_idx}")
        print("FULL CHUNK TEXT:")
        print(chunk.content)

    top_chunk = results[0][2] if results else None

    # STEP 7 — No LLM; trace answer composition
    section("STEP 7 — Answer composition (NO LLM in this pipeline)")
    print(
        "IMPORTANT: This RAG pipeline does NOT call an LLM for answer generation.\n"
        "AnswerGenerator uses rule-based extractors on retrieved chunk text.\n"
        "There is no system prompt, no LLM context window, no model API call."
    )
    if top_chunk:
        merged = top_chunk.content
        for raw_conf, cal_conf, chunk, _ in results[1:3]:
            if chunk.source == top_chunk.source:
                merged += " " + chunk.content
        print(f"\n--- Merged context passed to AnswerGenerator (top 3 same-source) ---")
        print(merged)

        print(f"\n--- _synthesize_structured_answer() direct call ---")
        structured = _synthesize_structured_answer(QUERY, merged)
        print(f"Output: {structured!r}")

        if structured and "Jurisdiction Primary Function" in structured:
            print("\n*** CORRUPTION DETECTED IN structured answer synthesis ***")
            hq_pat = r"([A-Za-z][A-Za-z\s]+)\s*\(HQ\)[^\n]*?([A-Za-z][A-Za-z\s,;&]+)"
            m = re.search(hq_pat, merged, flags=re.IGNORECASE)
            if m:
                print(f"Regex group(1) [city]: {m.group(1)!r}")
                print(f"Regex group(2) [description]: {m.group(2)!r}")

    # STEP 8
    section("STEP 8 — Raw answer output (before confidence packaging)")
    gen = AnswerGenerator()
    from app.rag.types import RetrievalResult

    retrieval_results = [
        RetrievalResult(
            content=chunk.content,
            source=chunk.source,
            category=chunk.category,
            confidence=cal_conf,
            chunk_id=chunk.chunk_id,
            page_number=chunk.page_number,
        )
        for raw_conf, cal_conf, chunk, _ in results[:3]
    ]
    generated = gen.generate(QUERY, retrieval_results)
    print(f"Raw answer text: {generated.answer}")
    print(f"sources_used: {generated.sources_used}")

    # STEP 9
    section("STEP 9 — Confidence calculation")
    print("Formula: calibrated = clamp((raw_cosine - 0.15) / (0.90 - 0.15), 0, 1)")
    print(f"Top-1 raw cosine: {results[0][0]:.6f}")
    print(f"Top-1 calibrated: {results[0][1]}")
    print(f"AnswerGenerator propagates top-1 calibrated as confidence_score: {generated.confidence_score}")
    print("No reranker, citation score, or LLM confidence — single retrieval score only.")

    # STEP 10 summary data
    section("STEP 10 — Corruption locus markers")
    for label, text in [
        ("raw_page8", page8_raw),
        ("normalized_page8", page8_normalized),
        ("top_retrieved_chunk", results[0][2].content if results else ""),
    ]:
        if "Jurisdiction Primary Function" in text.replace("\n", " "):
            print(f"'Jurisdiction Primary Function' appears in: {label}")
        if "Singapore (HQ)" in text:
            print(f"'Singapore (HQ)' appears in: {label}")


if __name__ == "__main__":
    main()
