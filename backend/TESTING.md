# Testing Guide — Enterprise Knowledge Assistant Backend

All commands assume you are in the `backend/` directory.

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Default test run

```bash
cd backend
python -m pytest
```

| Scope | Directory | Typical runtime |
|-------|-----------|-----------------|
| Unit tests | `tests/unit/` | ~10–20 s |
| Integration tests | `tests/integration/` | ~5–10 s |

Configuration: `pytest.ini` collects only `tests/unit` and `tests/integration`.

---

## Running subsets

```bash
# Unit tests only
python -m pytest -m unit

# Integration tests only
python -m pytest -m integration

# Single file
python -m pytest tests/unit/rag/test_query_processing.py

# Show slowest tests
python -m pytest --durations=20
```

---

## Retrieval evaluation benchmark

The canonical retrieval quality gate is the 144-case golden dataset benchmark:

```bash
cd backend
python -m app.evaluation.benchmark --label local_run --llm-provider none --no-compare
```

- Full dataset: `app/evaluation/dataset/golden_dataset_full.json`
- Fast subset: `app/evaluation/dataset/golden_dataset.json`
- Reports: `backend/evaluation_results/`

See **[docs/EVALUATION_FRAMEWORK.md](../docs/EVALUATION_FRAMEWORK.md)** and **[backend/scripts/README.md](scripts/README.md)** for comparison and diagnostic scripts.

---

## Diagnostic tools

| Tool | Command |
|------|---------|
| RAG trace | `python scripts/forensic_rag_trace.py` |
| Quality audit | `python scripts/rag_quality_audit.py` |
| Embedding eval | `python -m app.evaluation.embedding_benchmark` |

---

## Related documentation

- **[docs/05_testing_strategy.md](../docs/05_testing_strategy.md)** — testing philosophy and pyramid
- **[docs/MANUAL_TESTING_GUIDE.md](../docs/MANUAL_TESTING_GUIDE.md)** — full application manual testing
