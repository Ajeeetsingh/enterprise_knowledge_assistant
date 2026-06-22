# Testing Guide — Enterprise Knowledge Assistant Backend

This document describes how to run the backend test suite after Phase 5.1 and the
test-performance improvements applied in preparation for Phase 5.2.

All commands below assume you are in the `backend/` directory with dependencies
installed (`pip install -r requirements.txt`).

---

## Default test run

```bash
cd backend
python -m pytest
```

**What runs by default**

| Scope | Directory | Marker | Typical runtime |
|-------|-------------|--------|----------------|
| Unit tests | `tests/unit/` | `unit` | ~8–15 s |
| Integration tests | `tests/integration/` | `integration` | ~2–5 s |

**Total:** ~309 tests in ~10 seconds on a typical developer machine.

Configuration lives in `pytest.ini`:

```ini
testpaths =
    tests/unit
    tests/integration
```

Pytest auto-applies markers based on directory (`tests/conftest.py`).

---

## What is excluded from the default suite

The following are **not** collected when you run `python -m pytest`:

### 1. Legacy RAG pipeline script (`tests/rag/test_pipeline.py`)

This file contains four functions named `test_*`:

- `test_ingestion`
- `test_router`
- `test_rbac`
- `test_end_to_end`

They are **intentionally excluded** for three reasons:

1. **Wrong execution model** — They are part of a standalone script (`main()`),
   not pytest tests. Each function expects a `TestReport` instance and (for
   end-to-end) a fully initialized `EnterpriseRAG` object passed by `main()`.
   They do not use pytest fixtures and were never part of the CI-quality
   backend suite.

2. **Heavy dependencies** — They import `EnterpriseRAG`, which loads
   `sentence-transformers`, FAISS, and embedding models. That adds minutes to
   collection/runtime and is unsuitable for fast feedback on every commit.

3. **Explicit scope in `pytest.ini`** — Default collection is limited to
   `tests/unit` and `tests/integration` so developers get fast, reliable runs
   without PostgreSQL or GPU/ML stacks.

These tests were **not deleted or skipped in code**; they remain available for
manual RAG validation.

### 2. Root-level prototype tests (repository root)

The original Phase 00 prototype (`python test_pipeline.py` at the repo root) is
separate from the backend pytest suite. See the root [README](../README.md)
*Testing* section for that workflow.

---

## Running subsets

```bash
# Unit tests only
python -m pytest -m unit

# Integration tests only
python -m pytest -m integration

# Single file
python -m pytest tests/unit/test_authorization_service.py

# Show slowest tests
python -m pytest --durations=20
```

---

## Legacy RAG pipeline tests (manual execution)

Run the standalone RAG validation script directly:

```bash
cd backend
python tests/rag/test_pipeline.py
```

**Requirements**

- `sentence-transformers`, `faiss-cpu`, `torch`, and related packages installed
- Sample documents under `backend/tests/fixtures/sample_docs/`

**Output**

- Console summary of ingestion, routing, RBAC, and end-to-end checks
- `results/test_results.json` and `results/test_results.txt` at the repository
  root (written by the script)

**What it validates**

| Stage | Coverage |
|-------|----------|
| Ingestion | File loading, PDF support, category mapping |
| Router | HR / finance / security / employee query routing |
| RBAC | Allow/deny matrix per role and category |
| End-to-end | Full RAG queries with access control and citations |

Do **not** expect `python -m pytest tests/rag/` to work without refactoring;
collection fails when ML dependencies are missing and the functions are not
pytest-compatible.

---

## Test infrastructure (no application logic changes)

The backend suite uses test-only optimizations in `tests/conftest.py`:

| Patch | Purpose |
|-------|---------|
| Mock `check_database_connection` | Avoids ~260 s PostgreSQL TCP timeout per `TestClient` lifespan when Postgres is not running |
| No-op `engine.dispose` | Prevents slow teardown during integration tests |
| `TEST_PASSWORD_HASH` in `tests/constants.py` | Precomputed bcrypt hash for fixtures; real hashing remains in `test_password_service.py` |
| Session-scoped `TestClient` | Reuses one app lifespan per integration session |

Integration tests use an **in-memory SQLite** database via dependency overrides.
They do not require a running PostgreSQL instance for the default suite.

---

## Directory layout

```
backend/tests/
├── conftest.py          # Global patches and auto-markers
├── constants.py         # Shared test passwords / precomputed hashes
├── unit/                # Fast, isolated tests (default)
├── integration/         # API tests via TestClient (default)
├── rag/                 # Legacy RAG script (excluded from default pytest)
└── fixtures/            # Sample documents for RAG / service tests
```

---

## Planned migration: legacy RAG → pytest (future)

Before or during a later phase, the four legacy RAG checks will be migrated into
proper pytest tests:

| Step | Action |
|------|--------|
| 1 | Add `@pytest.mark.rag` (and optional `@pytest.mark.slow`) to `pytest.ini` |
| 2 | Refactor ingestion/router/RBAC/e2e into pytest modules with fixtures (`sample_docs`, mocked or session-scoped `EnterpriseRAG`) |
| 3 | Keep heavy e2e tests opt-in: `python -m pytest -m rag` (not part of default CI) |
| 4 | Retire or thin `tests/rag/test_pipeline.py` once parity is verified |
| 5 | Document CI matrix: fast job (`-m "unit or integration"`), nightly job (`-m rag`) |

**Target state**

- Default `python -m pytest` stays fast (~10 s, no ML stack required).
- RAG regression coverage moves to explicit, marked pytest tests.
- Legacy script remains available until migration is complete.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Suite takes hours | Postgres not running; old code path before conftest patch | Pull latest; ensure `tests/conftest.py` is present |
| `309 passed` vs expected `313` | Four legacy RAG functions excluded by design | Run `python tests/rag/test_pipeline.py` manually |
| `ModuleNotFoundError: sentence_transformers` | RAG deps not installed | Expected for default pytest; install ML deps only for manual RAG script |
| Integration auth tests slow (~0.3 s each) | Real bcrypt in login tests | Expected; password tests intentionally use real hashing |

---

## Related documentation

- Root [README](../README.md) — Phase 00 prototype testing (`test_pipeline.py`)
- [pytest.ini](./pytest.ini) — Default collection paths and markers
