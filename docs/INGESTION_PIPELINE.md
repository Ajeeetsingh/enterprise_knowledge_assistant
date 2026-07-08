# Ingestion Pipeline

Enterprise document ingestion transforms raw files into searchable, semantically chunked vectors stored in FAISS and BM25 indexes.

## Pipeline Overview

```
Document Upload
    ↓
Canonical Normalization (Phase 12.3A)
    ↓
Structure Extraction (Phase 12.3B)
    ↓
Semantic Chunking (Phase 12.4)
    ↓
Embedding
    ↓
Hybrid Indexing (FAISS + BM25)
```

Package layout:

```
backend/app/ingestion/
  normalization/       # Boilerplate, unicode, OCR cleanup
  structure/           # Headings, tables, lists
  semantic_chunking/   # SemanticChunkEngine
  embedding/           # SentenceTransformer provider
  stages/              # Pipeline stage orchestration
  pipeline.py          # End-to-end ingest
```

Production path: `DocumentService` → `IngestionPipeline` → `HybridIndexStore`.

---

## Normalization

`CanonicalNormalizer` cleans extracted text before structure analysis.

| Signal | Purpose |
|--------|---------|
| Boilerplate removal | Strip repeated headers/footers across pages |
| Unicode cleanup | Normalize characters and whitespace |
| OCR cleanup | Fix common OCR artifacts in PDF text |

Configuration (`Settings` / `.env`):

```env
NORMALIZATION_ENABLE_BOILERPLATE_REMOVAL=true
NORMALIZATION_ENABLE_UNICODE_CLEANUP=true
NORMALIZATION_ENABLE_OCR_CLEANUP=true
NORMALIZATION_MINIMUM_HEADER_FREQUENCY=2
NORMALIZATION_MINIMUM_FOOTER_FREQUENCY=2
NORMALIZATION_MAXIMUM_HEADER_LINES=4
NORMALIZATION_MAXIMUM_FOOTER_LINES=3
NORMALIZATION_BOILERPLATE_MIN_PAGE_RATIO=0.4
```

Package: `backend/app/ingestion/normalization/`

---

## Structure Extraction

`StructureExtractor` converts normalized text into a `StructuredDocument` with typed blocks (headings, paragraphs, tables, lists).

| Setting | Default | Purpose |
|---------|---------|---------|
| `STRUCTURE_EXTRACTION_ENABLED` | `true` | Master switch |
| `STRUCTURE_MAX_HEADING_LENGTH` | `200` | Heading detection limit |
| `STRUCTURE_MIN_TABLE_COLUMNS` | `2` | Minimum table width |
| `STRUCTURE_MIN_TABLE_ROWS` | `2` | Minimum table height |
| `STRUCTURE_TABLE_CONFIDENCE_THRESHOLD` | `0.55` | Table detection threshold |
| `STRUCTURE_MAX_LIST_NESTING_DEPTH` | `6` | List depth cap |

Package: `backend/app/ingestion/structure/`

---

## Semantic Chunking

`SemanticChunkEngine` replaces fixed-size character windows with structure-aware retrieval units.

### Strategy

1. Walk `StructuredDocument.blocks` in reading order.
2. Adaptively assemble chunks at semantic boundaries (headings, paragraphs, tables, lists).
3. Never split inside atomic blocks.
4. Post-process oversized tables/lists at row/item boundaries only.
5. Apply semantic overlap (section title / hierarchy) — not character overlap.

### Adaptive sizing

| Setting | Default | Purpose |
|---------|---------|---------|
| `SEMANTIC_MAX_PREFERRED_CHUNK_SIZE` | `1200` | Target upper bound |
| `SEMANTIC_SOFT_MAX_CHUNK_SIZE` | `1500` | Soft maximum |
| `SEMANTIC_ABSOLUTE_MAX_CHUNK_SIZE` | `1800` | Hard ceiling |
| `SEMANTIC_MIN_CHUNK_SIZE` | `80` | Minimum body size |
| `SEMANTIC_MAX_TABLE_CHUNK_SIZE` | `1800` | Table batch ceiling |
| `SEMANTIC_MAX_PARAGRAPH_MERGE` | `2` | Paragraph merge limit |
| `SEMANTIC_OVERLAP_ENABLED` | `true` | Semantic overlap on continuations |

### Stable chunk IDs

Block-derived IDs (`{source}::sem-h15-p16-t-table-5`) prevent renumbering when unrelated chunks change.

### Metadata

Each chunk carries `ChunkMetadata`: `chunk_type`, `section_title`, `hierarchy_path`, `page_start`/`page_end`, `reading_order`, content flags.

Package: `backend/app/ingestion/semantic_chunking/`

Legacy `chunk_text()` remains for tests; production uses `SemanticChunkEngine` only.

---

## Embedding

Production embeddings use `EmbeddingModelManager` (`app/embeddings/`) with the baseline model from `app/embeddings/models.json`.

| Setting | Description |
|---------|-------------|
| `EMBEDDING_LOCAL_ONLY` | Skip Hugging Face hub checks when models are pre-cached |

Ingestion uses `SentenceTransformerEmbeddingProvider` (`app/ingestion/embedding/`) backed by the shared manager.

Production baseline: `sentence-transformers/all-MiniLM-L6-v2` (see `app/rag/types.py`).

---

## Indexing

After embedding, chunks are written to `HybridIndexStore`:

- **FAISS** — dense cosine similarity (`storage/indexes/`)
- **BM25** — sparse lexical index (`storage/indexes/bm25_corpus.json`)

`DocumentService` and `index_bootstrap_service` keep both indexes synchronized on upload, reindex, and delete.

---

## Configuration Summary

All ingestion tunables are exposed via `Settings` and `.env.example`. No hardcoded production constants.

---

## Performance

- Normalization + structure: milliseconds per page (rule-based)
- Semantic chunking: proportional to block count
- Embedding: dominant cost; model loaded once via `EmbeddingModelManager.preload()`
- Index update: incremental FAISS + BM25 append per document

Measure embedding loads:

```bash
cd backend
py scripts/measure_performance.py --embedding
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Empty PDF text | Scanned PDF without OCR | Verify source PDF has extractable text |
| Missing tables | Low confidence threshold | Adjust `STRUCTURE_TABLE_CONFIDENCE_THRESHOLD` |
| Tiny chunks | `SEMANTIC_MIN_CHUNK_SIZE` too low | Review chunk validator warnings in logs |
| Index drift | BM25 out of sync | Restart service or delete `bm25_corpus.json` and re-ingest |
| HF download on startup | Model not cached | Pre-download or set `EMBEDDING_LOCAL_ONLY=true` |

---

## Testing

```bash
cd backend
py -m pytest tests/unit/test_document_ingestion.py tests/unit/test_ingestion_engine.py -q
```
