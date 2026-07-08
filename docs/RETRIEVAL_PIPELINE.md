# Retrieval Pipeline

Production retrieval orchestrates query intelligence, hybrid search, metadata rescoring, cross-encoder reranking, and LLM answer generation.

## End-to-End Flow

```
User Query
    ↓
Query Intelligence Engine
    ↓
Hybrid Retrieval (Dense FAISS + Sparse BM25 + Weighted RRF)
    ↓
Metadata-Aware Rescoring
    ↓
Multi-Query Merge (when applicable)
    ↓
Cross-Encoder Reranking
    ↓
Prompt Builder → LLM Provider → Answer + Citations
```

Entry point: `EnterpriseRAG._search()` in `backend/app/rag/engine.py`, invoked via `RagService`.

---

## Query Processing

Rule-based query intelligence runs before hybrid retrieval (`app/rag/query_processing/`).

### Capabilities

| Component | Description |
|-----------|-------------|
| Classification | 13 categories (entity, financial, policy, security, etc.) |
| Acronym expansion | Append expansions, keep original (`HQ` + `headquarters`) |
| Synonym expansion | Configurable synonym dictionary |
| Entity normalization | Alias → canonical form (`ceo` → `Chief Executive Officer`) |
| Multi-query generation | Template variants capped by `MAX_GENERATED_QUERIES` |
| Strategy selection | Adjust sparse/dense weights, metadata multiplier, rerank pool |

### Configuration

```env
QUERY_INTELLIGENCE_ENABLED=true
QUERY_EXPANSION_ENABLED=true
MULTI_QUERY_ENABLED=true
MAX_GENERATED_QUERIES=4
ENTITY_NORMALIZATION_ENABLED=true
SYNONYM_EXPANSION_ENABLED=true
STRATEGY_SELECTION_ENABLED=true
```

Rules: `backend/app/rag/query_processing/rules.json`

### Fallback

Processing failures log a warning and fall back to the original query. Retrieval is never blocked.

---

## Hybrid Retrieval

Combines dense FAISS embeddings with sparse BM25 via weighted Reciprocal Rank Fusion (RRF).

### Fusion

```
fusion_score = dense_weight × 1/(RRF_K + dense_rank)
             + sparse_weight × 1/(RRF_K + sparse_rank)
```

Intent-based routing adjusts weights (numeric/entity → favor sparse; general → favor dense).

### Configuration

```env
HYBRID_ENABLED=true
SPARSE_WEIGHT=1.0
DENSE_WEIGHT=1.0
RRF_K=60
BM25_K1=1.5
BM25_B=0.75
TOP_K_DENSE=20
TOP_K_SPARSE=20
TOP_K_FINAL=5
```

Package: `backend/app/rag/hybrid/`

### Explainability

`RetrievalResult` exposes `dense_rank`, `sparse_rank`, `fusion_score`, `fusion_explanation`, `source_retrievers`.

---

## Metadata Retrieval

Deterministic metadata rescoring on fused candidates (`app/rag/metadata_retrieval/`).

### Signals

- Heading / section-title / hierarchy token overlap
- Chunk-type alignment with detected intent
- Section, document, and reading-order continuity

### Configuration

```env
METADATA_RETRIEVAL_ENABLED=true
METADATA_MAX_BONUS=0.15
METADATA_HEADING_SIMILARITY_WEIGHT=0.04
METADATA_TABLE_INTENT_BOOST=0.05
...
```

Set `METADATA_RETRIEVAL_ENABLED=false` for cosine-only ranking.

### Explainability

`raw_cosine_score`, `metadata_bonus`, `final_score`, `score_explanation`, `detected_intent`, `chunk_type`.

---

## Cross-Encoder Reranking

Reorders top-N metadata candidates using a registry-configured cross-encoder (`app/rag/reranking/`).

### Models (`models.json`)

| Registry ID | Model |
|-------------|-------|
| `ms-marco-minilm-l6-v2` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (default) |
| `ms-marco-minilm-l12-v2` | `cross-encoder/ms-marco-MiniLM-L-12-v2` |
| `bge-reranker-base` | `BAAI/bge-reranker-base` |
| `bge-reranker-large` | `BAAI/bge-reranker-large` |

### Configuration

```env
RERANKING_ENABLED=true
RERANK_TOP_N=20
RERANK_MODEL=ms-marco-minilm-l6-v2
RERANK_MAX_BATCH_SIZE=16
RERANK_MAX_SEQUENCE_LENGTH=512
```

Batch inference with GPU/CPU auto-selection. Failsafe: returns hybrid+metadata ordering on error.

---

## Prompt Building

`PromptBuilder` (`app/llm/prompt_builder.py`) assembles system instructions, retrieved chunks with page metadata, optional conversation history, and the user question.

Conversation history is injected into the **prompt only** — retrieval embeds the current question alone.

---

## LLM Generation

Provider-based generation (`app/llm/`) with `AnswerGenerator` fallback.

### Configuration

```env
LLM_PROVIDER=groq          # groq | openai | gemini | ollama | none
LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1024
LLM_FALLBACK_ENABLED=true
```

### Behavior

- Citations built from retrieved chunks (LLM does not invent sources)
- `confidence_score` = top retrieval calibrated confidence
- `LLM_PROVIDER=none` uses rule-based `AnswerGenerator` only

Package: `backend/app/llm/providers/`

---

## Configuration

All retrieval stages load settings from `app/config.py` via stage-specific `*Settings.from_settings()` adapters. See `.env.example` for the complete list.

---

## Performance

| Stage | Typical overhead |
|-------|------------------|
| Query intelligence | < 1 ms (rule-based) |
| Hybrid retrieval | 20–50 ms + BM25 |
| Metadata rescoring | 5–15 ms |
| Cross-encoder rerank | 50 ms–2 s (CPU, 20 candidates) |
| LLM generation | Provider-dependent |

Measure components:

```bash
cd backend
py scripts/measure_performance.py --query
py scripts/measure_performance.py --reranker
py scripts/measure_performance.py --full
```

---

## Debugging

| Tool | Command |
|------|---------|
| RAG trace | `py scripts/forensic_rag_trace.py` |
| Quality audit | `py scripts/rag_quality_audit.py` |
| Retrieval benchmark | `py scripts/benchmark.py --retrieval` |
| Compare runs | `py scripts/compare_benchmarks.py --baseline A.json --current B.json` |

Structured logs emit per-stage latency, fusion statistics, reranking telemetry, and query intelligence metadata.

---

## Testing

```bash
cd backend
py -m pytest tests/unit/rag/ -q
```

Covers hybrid, metadata, reranking, and query processing with engine integration tests.
