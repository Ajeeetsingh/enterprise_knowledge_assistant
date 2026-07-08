# Backend Scripts

Operational and diagnostic scripts for the Enterprise Knowledge Assistant.  
Production retrieval benchmarks use `app.evaluation.benchmark` (preferred) or the unified CLI below.

## Benchmarking

| Script | Purpose |
|--------|---------|
| `benchmark.py` | Unified benchmark runner (`--retrieval`, `--embedding`, `--hybrid`, `--reranker`, `--full`) |
| `compare_benchmarks.py` | Compare benchmark JSON reports (`--baseline`, `--current`, `--latest`, `--all`) |
| `build_golden_dataset.py` | Regenerate golden evaluation dataset |

```bash
cd backend
py scripts/benchmark.py --retrieval --label my_run --llm-provider none --no-compare
py scripts/compare_benchmarks.py --latest
```

## Performance measurement

| Script | Purpose |
|--------|---------|
| `measure_performance.py` | Unified profiler (`--embedding`, `--retrieval`, `--reranker`, `--query`, `--full`) |

```bash
cd backend
py scripts/measure_performance.py --full
```

## Diagnostics

| Script | Purpose |
|--------|---------|
| `forensic_rag_trace.py` | Read-only RAG retrieval trace for a single query |
| `rag_quality_audit.py` | RAG quality audit against corpus PDFs |

## Documentation

- **[docs/EVALUATION_FRAMEWORK.md](../../docs/EVALUATION_FRAMEWORK.md)** — benchmark framework, metrics, golden datasets
- **[docs/RETRIEVAL_PIPELINE.md](../../docs/RETRIEVAL_PIPELINE.md)** — retrieval, reranking, query intelligence
- **[docs/INGESTION_PIPELINE.md](../../docs/INGESTION_PIPELINE.md)** — ingestion, chunking, embedding

## Embedding evaluation

Use the module entry point:

```bash
cd backend
py -m app.evaluation.embedding_benchmark
```

Or via the unified benchmark script:

```bash
py scripts/benchmark.py --embedding
```
