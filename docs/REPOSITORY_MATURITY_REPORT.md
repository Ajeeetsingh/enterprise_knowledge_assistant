# Repository Maturity Cleanup Report

**Date:** 2026-07-07  
**Scope:** Documentation consolidation, script unification, repository cleanup (Phases A–F)  
**Production behavior:** Unchanged — no API, retrieval, ingestion, embedding, or evaluation logic modifications.

---

## Summary

The repository was reorganized to present a mature production layout: three consolidated architecture guides, three unified backend operational scripts, two unified root utility scripts, and updated cross-references throughout README and testing documentation.

---

## Phase A — Documentation Consolidation

### Created (merged)

| New file | Merged from |
|----------|-------------|
| `docs/INGESTION_PIPELINE.md` | `SEMANTIC_CHUNKING.md`, normalization/structure/embedding/indexing sections |
| `docs/RETRIEVAL_PIPELINE.md` | `HYBRID_RETRIEVAL.md`, `METADATA_AWARE_RETRIEVAL.md`, `QUERY_INTELLIGENCE.md`, `CROSS_ENCODER_RERANKING.md`, `LLM_GENERATION.md` |
| `docs/EVALUATION_FRAMEWORK.md` | `EMBEDDING_EVALUATION.md`, `RETRIEVAL_EVALUATION.md` |

### Removed (obsolete implementation docs)

- `docs/SEMANTIC_CHUNKING.md`
- `docs/HYBRID_RETRIEVAL.md`
- `docs/METADATA_AWARE_RETRIEVAL.md`
- `docs/QUERY_INTELLIGENCE.md`
- `docs/CROSS_ENCODER_RERANKING.md`
- `docs/LLM_GENERATION.md`
- `docs/EMBEDDING_EVALUATION.md`
- `docs/RETRIEVAL_EVALUATION.md`

### Kept as standalone

- `docs/01_product_vision.md`
- `docs/02_system_architecture.md`
- `docs/03_development_principles.md`
- `docs/05_testing_strategy.md`
- `docs/06_deployment_guide.md`
- `docs/07_future_roadmap.md`
- `docs/08_ai_development_handbook.md`
- `docs/MANUAL_TESTING_GUIDE.md`
- `docs/ARCHITECTURE_CLEANUP_REPORT.md`

---

## Phase B — Backend Script Cleanup

### Created (consolidated)

| New script | Replaces |
|------------|----------|
| `backend/scripts/compare_benchmarks.py` | `compare_hybrid_benchmark.py`, `compare_rerank_benchmark.py`, `compare_query_intelligence_benchmark.py` |
| `backend/scripts/measure_performance.py` | `measure_embedding_loads.py`, `measure_query_intelligence_performance.py`, `measure_reranking_performance.py` |
| `backend/scripts/benchmark.py` | `run_retrieval_benchmark.py` |

### Removed

- `backend/scripts/compare_hybrid_benchmark.py`
- `backend/scripts/compare_rerank_benchmark.py`
- `backend/scripts/compare_query_intelligence_benchmark.py`
- `backend/scripts/measure_embedding_loads.py`
- `backend/scripts/measure_reranking_performance.py`
- `backend/scripts/measure_query_intelligence_performance.py`
- `backend/scripts/run_retrieval_benchmark.py`

### Kept (intentionally)

| Script | Reason |
|--------|--------|
| `rag_quality_audit.py` | Corpus quality diagnostics — unique, actively used |
| `forensic_rag_trace.py` | Single-query RAG trace — unique diagnostic |
| `build_golden_dataset.py` | Golden dataset regeneration — separate workflow |
| `README.md` | Script index (updated) |

---

## Phase C — Root Scripts Cleanup

### Created

| Script | Purpose |
|--------|---------|
| `scripts/seed_database.py` | Unified seeder (`--roles`, `--admin`, `--demo`, `--all`) |
| `scripts/setup_manual_testing.py` | Runs `seed_database.py --all` |

### Moved (logic preserved)

- `scripts/seed_*.py` → `scripts/seeding/` (roles, admin, demo users, demo data)

### Removed (duplicate launchers only)

Root-level `seed_*.py` and `generate_gtfs_*.py` launchers (replaced by `seed_database.py`; seeding logic retained under `seeding/`).

> **2026-07-08 follow-up:** `scripts/document_generators/` and `scripts/generate_documents.py` were later removed. The committed GTFS PDFs in `data/` are the static evaluation corpus.

### Updated

- `scripts/setup_manual_testing.py` — now calls `seed_database.py --all`

### Kept

- `scripts/run_demo.py` — Phase 00 prototype demo launcher (unchanged)

---

## Phase D — Repository Cleanup

| Action | Result |
|--------|--------|
| `backend/tests/rag/` | Already empty — no action needed |
| `scripts/__pycache__/` | Removed (`.pyc` artifacts) |
| `.gitignore` | Already excludes `__pycache__/` and `*.pyc` |
| `backend/pytest-phase-*.txt` | Not present in workspace |
| `backend/scripts/_audit_*.py` | Not present in workspace |

No orphaned production modules were removed — grep confirmed no dangling imports from deleted scripts.

---

## Phase E — Documentation Updates

| File | Changes |
|------|---------|
| `README.md` | Links to consolidated pipeline docs; `benchmark.py` usage |
| `folder_structure.md` | Updated `docs/` and `scripts/` tree |
| `backend/scripts/README.md` | Unified script reference |
| `docs/MANUAL_TESTING_GUIDE.md` | `seed_database.py` workflow |
| `backend/TESTING.md` | `EVALUATION_FRAMEWORK.md` reference |
| `docs/phases/phase_12_*.md` | Phase doc links updated |

---

## Phase F — Validation

### Pytest

```
1124 passed, 1 failed, 4 warnings (124s)
```

**Failure (pre-existing, unrelated to cleanup):**

- `tests/unit/test_jwt_service.py::test_invalid_signature_rejection` — tampered-token edge case did not raise `TokenInvalidError`. No JWT or auth code was modified in this cleanup.

### Retrieval benchmark (144 cases)

Command:

```bash
cd backend
py scripts/benchmark.py --retrieval --label maturity_cleanup --llm-provider none --no-compare
```

| Metric | `post_cleanup` (baseline) | `maturity_cleanup` (this run) | Δ |
|--------|---------------------------|-------------------------------|---|
| Recall@1 | 32.6% | 32.6% | 0.0 |
| Recall@3 | 63.2% | 63.2% | 0.0 |
| Recall@5 | 82.6% | 82.6% | 0.0 |
| MRR | 0.507 | 0.507 | 0.0 |

Metrics are **identical** to the post-architecture-cleanup baseline — within normal run-to-run variance (zero delta on retrieval metrics).

Report: `backend/evaluation_results/maturity_cleanup.json`

### Import / CLI checks

- `scripts/seed_database.py --help` — OK
- `backend/scripts/benchmark.py` — completed full 144-case run via unified entry point

---

## Broken References Fixed

- `README.md` — obsolete per-feature doc links → consolidated guides
- `backend/TESTING.md` — `RETRIEVAL_EVALUATION.md` → `EVALUATION_FRAMEWORK.md`
- `docs/MANUAL_TESTING_GUIDE.md` — seed script references
- `docs/phases/phase_12_production_hardening_security_&_performance_optimization.md` — phase doc map
- `backend/tests/integration/test_evaluation_framework.py` — argv label `benchmark`
- `scripts/seeding/*.py` — docstrings and error messages

---

## Files Intentionally Kept

| Path | Reason |
|------|--------|
| `scripts/seeding/*.py` | Reusable seeding modules called by `seed_database.py` |
| `data/*.pdf` | Static GTFS evaluation corpus (144-case benchmark) |
| `scripts/run_demo.py` | Legacy prototype demo — not part of consolidation scope |
| `backend/scripts/rag_quality_audit.py` | Unique diagnostic tool |
| `backend/scripts/forensic_rag_trace.py` | Unique diagnostic tool |
| `backend/scripts/build_golden_dataset.py` | Dataset maintenance workflow |
| `docs/ARCHITECTURE_CLEANUP_REPORT.md` | Prior cleanup audit trail |
| `docs/phases/` | Historical phase planning records |

---

## New Unified CLI Quick Reference

```bash
# Backend benchmarks
cd backend
py scripts/benchmark.py --retrieval --label my_run --llm-provider none --no-compare
py scripts/compare_benchmarks.py --latest
py scripts/measure_performance.py --full

# Root utilities
python scripts/seed_database.py --all
python scripts/setup_manual_testing.py
```
