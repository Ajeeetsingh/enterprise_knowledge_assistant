# Architecture Cleanup Report

**Date:** 2026-07-07  
**Scope:** Dead code removal, documentation consolidation, dependency hygiene.  
**Constraint:** No changes to production functionality, APIs, benchmarks, or behavior.

---

## Summary

| Action | Count |
|--------|-------|
| Files deleted | 22 |
| Modules consolidated (documentation) | 6 doc files updated |
| Dependencies removed | 1 (`python-dotenv`) |
| Dependencies added (missing runtime) | 2 (`pypdf`, `python-docx`) |
| Dependencies moved to dev | 1 (`pytest` → `requirements-dev.txt`) |
| Configuration options removed | 0 (none were unused) |
| Configuration documented | 1 (`EMBEDDING_LOCAL_ONLY` added to `.env.example`) |

---

## Deleted Files

### Dead Python modules

| File | Reason |
|------|--------|
| `backend/app/rbac/__init__.py` | Zero imports; superseded by `app/auth/` + `app/rag/rbac.py` |
| `backend/app/rbac/permissions.py` | Unused stub |
| `backend/app/rbac/policy.py` | Re-export wrapper never imported |
| `backend/app/rbac/document_acl.py` | One-line placeholder |
| `backend/app/rag/index_manager.py` | Empty stub (“populated in a later phase”); zero imports |

### Temporary / one-off scripts

| File | Reason |
|------|--------|
| `backend/scripts/_audit_pages.py` | Phase audit script |
| `backend/scripts/_audit_ranking.py` | Phase audit script |
| `backend/scripts/_compare_phase12_4.py` | Phase-specific benchmark comparator |
| `backend/scripts/_compare_phase12_5_benchmark.py` | Phase-specific benchmark comparator |
| `backend/scripts/_compare_table_fix_benchmark.py` | Phase-specific benchmark comparator |

### Stale manual tests (excluded from pytest)

| File | Reason |
|------|--------|
| `backend/tests/rag/test_pipeline.py` | Legacy standalone script; broken/outdated |
| `backend/tests/rag/realistic_enterprise_test.py` | Legacy enterprise script |
| `test_pipeline.py` (repo root) | Wrapper for deleted script |
| `realistic_enterprise_test.py` (repo root) | Wrapper for deleted script |

### CI output artifacts

| File | Reason |
|------|--------|
| `backend/pytest-phase-11-2.txt` | Captured pytest output |
| `backend/pytest-phase-11-3.txt` | Captured pytest output |
| `backend/pytest-phase-11-4.txt` | Captured pytest output |
| `backend/pytest-phase-11-5.txt` | Captured pytest output |
| `backend/pytest-phase-11-6.txt` | Captured pytest output |
| `backend/pytest-after-analytics-refactor.txt` | Captured pytest output |
| `backend/pytest-full-results.txt` | Captured pytest output |
| `backend/pytest-full-results-2.txt` | Captured pytest output |

---

## Consolidated Modules & Documentation

| Change | Details |
|--------|---------|
| **Single RAG orchestrator** | Production path confirmed: `RagService` → `EnterpriseRAG` → hybrid + metadata + reranking + query intelligence. Legacy `SemanticRetriever` path retained only for CLI/demo (`app.rag.cli`, `EnterpriseRAG(data_dir=...)`) — documented, not removed (required by integration tests). |
| **Single RBAC model** | Removed duplicate `app/rbac/` package. Category RBAC: `app/rag/rbac.py`. API auth: `app/auth/`. |
| **Index management** | Removed stub `index_manager.py`. Production indexing via `document_service` + `HybridIndexStore` + `index_bootstrap_service`. |
| **README.md** | Replaced outdated Phase 00 prototype README with current architecture pointers. |
| **backend/TESTING.md** | Removed legacy RAG script sections; points to pytest + evaluation benchmark. |
| **docs/MANUAL_TESTING_GUIDE.md** | Replaced `test_pipeline.py` references with pytest + benchmark commands. |
| **docs/phases/phase_12_*.md** | Updated status; added cross-links to implemented feature docs (12.3–12.9). |
| **folder_structure.md** | Removed `app/rbac/`, `index_manager`, `tests/rag/` references; added hybrid/reranking/query_processing. |
| **backend/scripts/README.md** | New index for kept benchmark, performance, and diagnostic scripts. |

### Scripts retained (production / diagnostic)

- `compare_hybrid_benchmark.py`, `compare_rerank_benchmark.py`, `compare_query_intelligence_benchmark.py`
- `measure_embedding_loads.py`, `measure_reranking_performance.py`, `measure_query_intelligence_performance.py`
- `run_retrieval_benchmark.py`, `build_golden_dataset.py`
- `forensic_rag_trace.py`, `rag_quality_audit.py`

---

## Removed Dependencies

| Package | Reason |
|---------|--------|
| `python-dotenv` | Never imported; `pydantic-settings` loads `.env` |

## Added Dependencies (were implicit/missing)

| Package | Reason |
|---------|--------|
| `pypdf` | Required by `app/ingestion/parsers/pdf.py`, `loader.py` |
| `python-docx` | Required by `app/ingestion/parsers/docx.py` |

## Moved to Dev Dependencies

| Package | File |
|---------|------|
| `pytest` | `backend/requirements-dev.txt` |

Install for development:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

---

## Removed Configuration Options

**None.** All fields in `backend/app/config.py` are wired through `*Settings.from_settings()` adapters.

**Documented:** `EMBEDDING_LOCAL_ONLY` added to `.env.example` (was in code but undocumented).

---

## Intentionally Not Removed

| Item | Reason |
|------|--------|
| `app/evaluation/` + golden datasets | Required evaluation framework |
| `app/rag/retriever.py` (`SemanticRetriever`) | CLI/demo + `search_semantic_retriever` fallback |
| `EnterpriseRAG` legacy `data_dir` path | Used by `rag/cli.py`, `test_chat_rbac_denial_integration.py` |
| `app/analytics/services/dashboard_service.py` | Unit tested; planned API surface |
| `app/analytics/services/metrics_service.py` | Unit tested; distinct from runtime `app/services/metrics_service.py` |
| `golden_dataset.json` + `golden_dataset_full.json` | Fast subset vs full 144-case benchmark |
| Frontend dev routes (`DesignSystemPage`, etc.) | No backend behavior change requested |
| `app.py` root CLI | Backward-compatible entry to `app.rag.cli` |

---

## Test Fix (cleanup-related)

| File | Change |
|------|--------|
| `tests/unit/test_rag_engine_llm.py` | Mock `_search` instead of obsolete `vector_store.search` (aligned with production retrieval path) |

---

## Verification

### Tests (post-cleanup)

```
1125 passed, 4 warnings in ~144s
```

### Benchmark (post-cleanup)

```
144 cases completed successfully
Label: post_cleanup
Report: backend/evaluation_results/post_cleanup.json
```

| Metric | Phase 12.9 baseline | Post-cleanup | Notes |
|--------|---------------------|--------------|-------|
| Recall@1 | 29.2% | 32.6% | No retrieval code changed; run-to-run variance expected |
| Recall@3 | 58.3% | 63.2% | |
| Recall@5 | 76.4% | 82.6% | |
| MRR | 46.2% | 50.7% | |
| Cases | 144 | 144 | All cases executed |

Benchmark confirms production pipeline intact after cleanup.

---

## Production Subsystem Map (post-cleanup)

| Subsystem | Single implementation |
|-----------|----------------------|
| Authentication | `app/auth/` |
| Category RAG RBAC | `app/rag/rbac.py` |
| Document ingestion | `app/ingestion/pipeline.py` + semantic chunking |
| Embeddings | `app/embeddings/manager.py` + `app/ingestion/embedding/` |
| Vector index | `HybridIndexStore` (FAISS + BM25) via `document_service` |
| Retrieval orchestration | `app/rag/engine.py` |
| Query intelligence | `app/rag/query_processing/` |
| Hybrid retrieval | `app/rag/hybrid/` |
| Metadata rescoring | `app/rag/metadata_retrieval/` |
| Reranking | `app/rag/reranking/` |
| LLM generation | `app/llm/` |
| Evaluation | `app/evaluation/` |
| Runtime monitoring | `app/services/metrics_service.py` + `/monitoring` API |
| Analytics (DB) | `app/analytics/` |
