"""RAG quality audit diagnostic — read-only investigation script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

PDF_PATH = BACKEND.parent / "data" / "GTFS-EXEC-001_Company_Overview.pdf"
QUERY = "What is the company headquarters?"

EVAL_QUESTIONS = [
    "What is the company headquarters?",
    "Who is the CEO?",
    "Who is the CTO?",
    "What is Project Phoenix?",
    "Which countries does GTFS operate in?",
    "What are the strategic priorities?",
    "What is the Atlas platform?",
    "What is the review date?",
    "Which regulator oversees Singapore?",
    "Which office serves as the Technology Centre of Excellence?",
]


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    # Import leaf modules directly to avoid circular imports via package __init__
    import importlib.util

    def _load(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    app_dir = BACKEND / "app"
    chunker_mod = _load("chunker", app_dir / "ingestion" / "chunker.py")
    pdf_mod = _load("pdf_parser", app_dir / "ingestion" / "parsers" / "pdf.py")

    from pypdf import PdfReader

    CHUNK_SIZE = chunker_mod.CHUNK_SIZE
    CHUNK_OVERLAP = chunker_mod.CHUNK_OVERLAP
    chunk_text = chunker_mod.chunk_text
    PdfParser = pdf_mod.PdfParser

    # categorizer is standalone
    import importlib
    categorizer = importlib.import_module("app.ingestion.categorizer")
    resolve_category = categorizer.resolve_category

    # types module (no heavy deps)
    types_mod = importlib.import_module("app.rag.types")
    EMBEDDING_MODEL_NAME = types_mod.EMBEDDING_MODEL_NAME
    calibrate_confidence = types_mod.calibrate_confidence
    _CALIBRATION_HIGH = types_mod._CALIBRATION_HIGH
    _CALIBRATION_LOW = types_mod._CALIBRATION_LOW
    _CALIBRATION_RANGE = types_mod._CALIBRATION_RANGE

    # faiss store - need to set up path
    faiss_mod = importlib.import_module("app.ingestion.vector_store.faiss_store")
    FaissVectorStore = faiss_mod.FaissVectorStore

    answer_mod = importlib.import_module("app.rag.answer_generator")
    AnswerGenerator = answer_mod.AnswerGenerator

    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        sys.exit(1)

    pdf_bytes = PDF_PATH.read_bytes()
    filename = PDF_PATH.name
    category = resolve_category(filename)

    # ------------------------------------------------------------------ Step 2: PDF parsing
    section("STEP 2 — Document Processing (PDF)")
    reader = PdfReader(str(PDF_PATH))
    print(f"PDF path: {PDF_PATH}")
    print(f"Total PDF pages (pypdf): {len(reader.pages)}")
    print(f"OCR enabled: No (text extraction only via pypdf)")

    parser = PdfParser()
    extracted = parser.parse(pdf_bytes, filename)
    page_markers = [ln for ln in extracted.split("\n") if ln.strip().startswith("<<<PAGE:")]
    print(f"Page markers emitted by parser: {len(page_markers)}")
    for m in page_markers[:5]:
        print(f"  {m}")
    if len(page_markers) > 5:
        print(f"  ... ({len(page_markers) - 5} more)")

    # Per-page text preview
    print("\nPer-page extraction preview (first 200 chars):")
    current_page = None
    page_text: dict[int, str] = {}
    for line in extracted.split("\n"):
        if line.strip().startswith("<<<PAGE:"):
            num = int(line.strip().replace("<<<PAGE:", "").replace(">>>", ""))
            current_page = num
            page_text[num] = ""
        elif current_page is not None:
            page_text[current_page] += line + "\n"

    for pg in sorted(page_text.keys())[:8]:
        preview = page_text[pg][:200].replace("\n", " ")
        print(f"  Page {pg}: {preview}...")

    # Search for HQ content in extracted text
    hq_idx = extracted.lower().find("headquarters")
    hq_idx2 = extracted.lower().find("(hq)")
    print(f"\n'headquarters' found at char {hq_idx}, '(HQ)' at char {hq_idx2}")
    if hq_idx >= 0:
        ctx = extracted[max(0, hq_idx - 100): hq_idx + 300]
        print(f"HQ context excerpt:\n{ctx[:400]}")

    # ------------------------------------------------------------------ Step 3: Chunking
    section("STEP 3 — Chunking Audit")
    chunks = chunk_text(extracted, filename, category)
    print(f"Chunk size setting: {CHUNK_SIZE} chars")
    print(f"Overlap setting: {CHUNK_OVERLAP} chars")
    print(f"Strategy: sentence/paragraph-aware greedy chunking with page markers")
    print(f"Recursive chunking: No")
    print(f"Semantic chunking: No (character/sentence boundary only)")
    print(f"Heading-aware: No")
    print(f"Total chunks generated: {len(chunks)}")

    sizes = [len(c.content) for c in chunks]
    if sizes:
        print(f"Avg chunk size: {sum(sizes)/len(sizes):.0f} chars")
        print(f"Min/Max chunk size: {min(sizes)} / {max(sizes)} chars")

    pages = {c.page_number for c in chunks}
    print(f"Page numbers assigned to chunks: {sorted(p for p in pages if p is not None)}")
    null_pages = sum(1 for c in chunks if c.page_number is None)
    print(f"Chunks with page_number=None: {null_pages}")

    print("\nAll chunks:")
    for c in chunks:
        tokens_est = len(c.content.split())
        print(f"\n--- {c.chunk_id} ---")
        print(f"  source={c.source} category={c.category} page={c.page_number}")
        print(f"  chars={len(c.content)} est_tokens~{tokens_est}")
        print(f"  preview: {c.content[:300]}...")
        if "headquarters" in c.content.lower() or "(hq)" in c.content.lower():
            print("  *** CONTAINS HQ CONTENT ***")

    # Large table chunks
    large = [c for c in chunks if len(c.content) > 700]
    print(f"\nChunks near/over size limit (>700 chars): {len(large)}")

    # ------------------------------------------------------------------ Step 4 & 5: Embeddings + Search
    section("STEP 4 — Embeddings")
    print(f"Model: {EMBEDDING_MODEL_NAME}")
    store = FaissVectorStore()
    model = store._load_model()
    texts = [c.content for c in chunks]
    import numpy as np
    import faiss
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)
    print(f"Dimensions: {embeddings.shape[1]}")
    print(f"Distance metric: Inner product on L2-normalized vectors (= cosine similarity)")
    print(f"Normalization: faiss.normalize_L2 before index add and query encode")
    print(f"Vectors generated: {len(embeddings)}")

    emb_lists = [embeddings[i].tolist() for i in range(len(chunks))]
    store.add_chunks(chunks, emb_lists, document_id="GTFS-EXEC-001")

    section("STEP 1 & 5 — Pipeline Trace + Top-20 Search")
    print(f"Query: {QUERY}")
    query_vec = store._encode_query(QUERY)
    print(f"Embedding model: {store.model_name}")
    print(f"Embedding dimension: {store.dimension}")
    print(f"Index: FAISS IndexFlatIP (in-process)")
    print(f"Top-K (engine default): 3")

    # Raw top-20 without RBAC filter
    search_k = min(len(chunks), 20)
    scores, indices = store._index.search(query_vec, search_k)

    print(f"\nTop-{search_k} raw results (before RBAC, showing raw + calibrated scores):")
    for rank, (raw, idx) in enumerate(zip(scores[0], indices[0]), 1):
        if idx < 0:
            continue
        c = chunks[idx]
        cal = calibrate_confidence(float(raw))
        print(f"\n  Rank {rank}: raw={raw:.4f} calibrated={cal:.4f} ({cal*100:.1f}%)")
        print(f"    chunk_id={c.chunk_id} page={c.page_number} category={c.category}")
        print(f"    preview: {c.content[:200]}...")

    # Engine path
    section("STEP 6 — Confidence Calculation")
    print(f"Formula: calibrated = clamp((raw_cosine - {_CALIBRATION_LOW}) / {_CALIBRATION_RANGE}, 0, 1)")
    print(f"  _CALIBRATION_LOW  = {_CALIBRATION_LOW}  → maps to 0%")
    print(f"  _CALIBRATION_HIGH = {_CALIBRATION_HIGH} → maps to 100%")
    print(f"Displayed confidence = calibrated score of TOP-1 chunk only")
    print(f"NOT based on: LLM certainty, answer quality, hybrid score")
    print(f"\nTheoretical max displayed confidence:")
    print(f"  raw=0.90 → {calibrate_confidence(0.90)*100:.1f}%")
    print(f"  raw=0.85 → {calibrate_confidence(0.85)*100:.1f}%")
    print(f"  raw=0.70 → {calibrate_confidence(0.70)*100:.1f}%")
    print(f"  raw=0.60 → {calibrate_confidence(0.60)*100:.1f}%")
    print(f"\nWhy ~63% cap observed:")
    print(f"  If raw cosine ≈ 0.60: calibrated = (0.60-0.15)/0.75 = 0.60 → 60%")
    print(f"  If raw cosine ≈ 0.62: calibrated = (0.62-0.15)/0.75 = 0.627 → 63%")
    print(f"  MiniLM-L6-v2 rarely exceeds ~0.75 raw for domain Q&A even on correct chunks")

    results = store.search(QUERY, top_k=3, allowed_categories={"general", "finance", "hr", "admin"})
    print(f"\nTop-3 after category filter:")
    for r in results:
        print(f"  chunk={r.chunk_id} page={r.page_number} confidence={r.confidence} ({r.confidence*100:.1f}%)")

    section("STEP 7 & 8 — Prompt / Answer Generation")
    print("System prompt: NONE — this RAG pipeline does NOT call an external LLM")
    print("Answer generation: rule-based extractors + regex synthesis in AnswerGenerator")
    print("Retrieved context passed to AnswerGenerator._compose_answer() as merged text")

    context = " ".join(r.content for r in results)
    print(f"\nMerged context length: {len(context)} chars (~{len(context.split())} tokens est.)")
    print(f"Context preview:\n{context[:800]}...")

    gen = AnswerGenerator()
    answer = gen.generate(QUERY, results)
    print(f"\nFinal answer: {answer.answer}")
    print(f"Confidence: {answer.confidence_score} ({answer.confidence_score*100:.1f}%)")
    print(f"Sources: {answer.sources_used}")

    section("STEP 9 — Retrieval Evaluation (10 questions)")
    for q in EVAL_QUESTIONS:
        res = store.search(q, top_k=3, allowed_categories={"general", "finance", "hr", "admin"})
        ans = gen.generate(q, res)
        top = res[0] if res else None
        print(f"\nQ: {q}")
        if top:
            print(f"  Top chunk: {top.chunk_id} page={top.page_number}")
            print(f"  Raw context preview: {top.content[:150]}...")
            print(f"  Confidence: {ans.confidence_score*100:.1f}%")
            print(f"  Answer: {ans.answer[:200]}")
        else:
            print("  NO RESULTS")

    section("STEP 10 — Improvement Ranking (by expected impact for this corpus)")
    improvements = [
        ("Cross-encoder reranking", "High", "Re-order top-20 by query-chunk relevance; fixes ranking when embedding score is flat"),
        ("Better embedding model (e.g. bge-base)", "High", "Raise raw cosine 0.55→0.75+ for factual matches"),
        ("Table-aware chunking (row-per-chunk)", "High", "Fixes garbled table extraction; improves HQ/regional office queries"),
        ("Heading-aware chunking", "Medium", "Preserves section context (CEO, Strategy, etc.)"),
        ("Hybrid BM25 + vector", "Medium", "Exact term matches (CEO, Phoenix, Atlas) when embeddings miss"),
        ("Fix confidence calibration (use raw score or percentile)", "Medium", "Remove artificial 63% ceiling perception"),
        ("Metadata-aware retrieval (page, section filter)", "Medium", "Route queries to relevant sections"),
        ("Parent-child retrieval", "Medium", "Retrieve small chunk, expand to section context"),
        ("Dynamic Top-K", "Low", "Minor gain; top-3 usually sufficient"),
        ("Context compression", "Low", "No LLM in pipeline currently"),
        ("Increase chunk overlap", "Low", "Already 150; marginal"),
    ]
    for name, priority, impact in improvements:
        print(f"  [{priority}] {name}: {impact}")


if __name__ == "__main__":
    main()
