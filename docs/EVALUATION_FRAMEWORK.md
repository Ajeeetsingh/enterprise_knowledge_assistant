# Evaluation Framework

Enterprise-grade evaluation for retrieval quality, embedding model comparison, and regression tracking. Runs the **real production pipeline** without modifying production behavior.

## Architecture

```
backend/app/evaluation/
├── benchmark.py              # Retrieval benchmark CLI
├── embedding_benchmark.py    # Multi-model embedding comparison CLI
├── bootstrap.py                # Corpus indexing via production pipeline
├── runner.py                   # EvaluationRunner → EnterpriseRAG
├── metrics.py                  # Semantic Recall@K, MRR, precision
├── semantic_matcher.py         # Semantic relevance (not chunk-index only)
├── answer_evaluator.py         # Answer evaluation modes
├── report.py                   # Console, JSON, CSV, HTML dashboard
├── history.py                  # latest_run.json, best_run.json, regression
└── dataset/
    ├── golden_dataset.json         # Fast subset
    └── golden_dataset_full.json    # 144-case GTFS benchmark
```

Design principles:

1. No production code changes — evaluation imports production components.
2. Real pipeline only — no mocked retrieval or embeddings.
3. Semantic evaluation — relevance by document, page, section, not chunk index alone.
4. Regression support — every run stored with comparison deltas.

---

## Benchmark Framework

### Running evaluations

```bash
cd backend

# Full 144-case retrieval benchmark (recommended)
py scripts/benchmark.py --retrieval --label my_run --llm-provider none --no-compare

# Fast subset
py scripts/benchmark.py --retrieval \
  --dataset app/evaluation/dataset/golden_dataset.json

# Embedding model comparison
py scripts/benchmark.py --embedding --model e5-base-v2
```

### CLI options (retrieval)

| Flag | Description |
|------|-------------|
| `--dataset` | Golden dataset JSON path |
| `--corpus` | Document corpus directory |
| `--results-dir` | Output directory |
| `--top-k` | Retrieval depth for metrics (default 5) |
| `--llm-provider` | Override provider (`none` for retrieval-only) |
| `--label` | Export file prefix |
| `--no-compare` | Skip regression comparison |

---

## Semantic Evaluation

Phase 12.6+ uses semantic relevance matching (`semantic_matcher.py`):

- Expected document match
- Page match (±1 page tolerance)
- Section / hierarchy overlap
- Notes / answer token overlap

Metrics driven by semantic match, not legacy chunk-index equality.

| Metric | Definition |
|--------|------------|
| **Recall@1** | Semantic match at rank 1 |
| **Recall@3/5** | Semantic match in top 3/5 |
| **MRR** | Mean reciprocal rank of first semantic match |
| **Context Precision** | Fraction of retrieved chunks that are relevant |

### Failure types

`retrieval_failure`, `ranking_failure`, `generation_failure`, `citation_failure`, `hallucination`, `context_noise`, `confidence_issue`, etc.

---

## Embedding Evaluation

Compare candidate embedding models without changing production (`app/evaluation/embedding_eval/`).

### Supported models (`app/embeddings/models.json`)

| ID | Model | Role |
|----|-------|------|
| `minilm-l6-v2` | `all-MiniLM-L6-v2` | Production baseline |
| `bge-base-en-v1.5` | `BAAI/bge-base-en-v1.5` | Candidate |
| `e5-base-v2` | `intfloat/e5-base-v2` | Candidate |
| ... | ... | ... |

### Running

```bash
py scripts/benchmark.py --embedding --model e5-base-v2 --label e5_eval
# or
py -m app.evaluation.embedding_benchmark --model e5-base-v2
```

Each model gets an isolated index under `evaluation_results/embedding_storage/{model_id}/`.

**Do not switch production embedding without benchmark evidence.**

---

## Metrics Reference

### Retrieval

Recall@1, Recall@3, Recall@5, MRR, Precision@K, Top-1/3 Correct %

### Answer & citation (with LLM enabled)

Answer Accuracy, Citation Accuracy, Hallucination Rate

### Latency

Avg retrieval / generation / total latency, P50/P95

### Best-run weighting

```
score = 0.35 × Recall@1 + 0.25 × MRR + 0.25 × Answer Accuracy + 0.15 × Citation Accuracy
```

---

## Golden Datasets

| File | Cases | Use |
|------|-------|-----|
| `golden_dataset_full.json` | 144 | Full GTFS benchmark |
| `golden_dataset.json` | Subset | Fast local testing |

**Corpus:** The GTFS PDFs live in `data/` at the repository root (static, committed). The retrieval benchmark indexes these files — no generator scripts are required.

Regenerate golden dataset JSON:

```bash
py scripts/build_golden_dataset.py
```

### Case schema

Required: `id`, `question`, `expected_answer`, `expected_document`

Optional: `expected_page`, `expected_chunks`, `role`, `authorized_sources`, `difficulty`, `query_category`, `answer_match_mode`

---

## Reports

Output directory: `backend/evaluation_results/`

| Artifact | Description |
|----------|-------------|
| `{label}.json` | Full benchmark report |
| `{label}_dashboard.html` | Interactive dashboard |
| `{label}_questions.csv` | Per-question results |
| `latest_run.json` | Most recent run |
| `best_run.json` | Best weighted score |
| `artifacts/{run_id}/` | Per-question JSON artifacts |

### Comparing runs

```bash
py scripts/compare_benchmarks.py \
  --baseline evaluation_results/phase12_8_rerank.json \
  --current evaluation_results/post_cleanup.json

py scripts/compare_benchmarks.py --latest
py scripts/compare_benchmarks.py --all
```

---

## Running Evaluations (quick reference)

```bash
# Tests
py -m pytest tests/unit/evaluation tests/integration/test_evaluation_framework.py -q

# Full benchmark
py scripts/benchmark.py --retrieval --label production_check --llm-provider none

# Compare
py scripts/compare_benchmarks.py --baseline evaluation_results/latest_run.json \
  --current evaluation_results/best_run.json
```

---

## Interpreting Results

### Strong retrieval targets

- Recall@1 ≥ 30% (GTFS 144-case corpus with semantic eval)
- MRR ≥ 0.45
- Recall@5 ≥ 75%

Run-to-run variance of ±3 pp is normal due to reranker non-determinism on CPU.

### Common failure reasons

| Reason | Meaning |
|--------|---------|
| `expected_semantic_region_not_in_top_k` | Retrieval missed expected content |
| `expected_semantic_region_not_rank_1` | Found but not ranked first |
| `answer_mismatch` | Generated answer failed evaluation |

---

## Future Extensions

- LLM judge for semantic answer evaluation
- CI benchmark gate on Recall@1 regression
- Automated embedding promotion workflow
