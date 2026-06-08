# Enterprise RAG — Architecture

This document describes the architecture of the Enterprise RAG Intelligence system: how documents are ingested, embedded, stored, routed, authorized, and turned into answers.

## System Overview

The pipeline is modular. Each layer maps to a dedicated Python module and is orchestrated by `app.py` through the `EnterpriseRAG` class.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY + ROLE                              │
│                         e.g. "finance | Q3 revenue?"                        │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION  (app.py)                             │
│                    EnterpriseRAG.initialize() / .query()                      │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────────┐
│  QUERY ROUTER    │      │   RBAC LAYER     │      │  ANSWER GENERATION   │
│  (router.py)     │─────▶│   (rbac.py)      │      │  (retriever.py)      │
│                  │      │                  │      │                      │
│  Classify intent │      │  Allow / Deny    │      │  Extractive answer   │
│  → hr | finance  │      │  by role         │      │  from top chunk      │
│    | security    │      │                  │      │                      │
│    | employee    │      │                  │      │                      │
└────────┬─────────┘      └────────┬─────────┘      └──────────▲───────────┘
         │                         │                            │
         │              access denied → stop                    │
         │                         │ access granted             │
         └─────────────────────────┼────────────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │     VECTOR DATABASE (FAISS)  │
                    │       (retriever.py)         │
                    │                              │
                    │  IndexFlatIP + metadata      │
                    │  Category-filtered search    │
                    └──────────────▲───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │     EMBEDDING LAYER          │
                    │     (retriever.py)           │
                    │                              │
                    │  all-MiniLM-L6-v2            │
                    │  384-dim vectors, L2 norm    │
                    └──────────────▲───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │     INGESTION LAYER          │
                    │     (loader.py)              │
                    │                              │
                    │ pdf / txt / csv / json → chunks │
                    └──────────────▲───────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   hr_policy.txt          finance_report.txt        security_logs.json
                                                    employees.csv
```

---

## Index-Time vs Query-Time Flow

```
INDEX TIME (startup)                    QUERY TIME (per request)
─────────────────────                   ─────────────────────────

  data/*.pdf|txt|csv|json                 User query + role
         │                                       │
         ▼                                       ▼
  ┌─────────────┐                         ┌─────────────┐
  │  Ingestion  │                         │   Router    │
  │   Layer     │                         │   Layer     │
  └──────┬──────┘                         └──────┬──────┘
         │                                       │
         ▼                                       ▼
  ┌─────────────┐                         ┌─────────────┐
  │  Embedding  │                         │    RBAC     │─── DENY → empty response
  │   Layer     │                         │   Layer     │
  └──────┬──────┘                         └──────┬──────┘
         │                                  ALLOW │
         ▼                                       ▼
  ┌─────────────┐                         ┌─────────────┐
  │   FAISS     │◀──── semantic search ───│  Retriever  │
  │   Index     │                         │  (query)    │
  └─────────────┘                         └──────┬──────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   Answer    │
                                          │ Generation  │
                                          └──────┬──────┘
                                                 │
                                                 ▼
                                    { answer, source, confidence }
```

---

## 1. Ingestion Layer

**Module:** `loader.py`

The ingestion layer reads raw enterprise documents from the `data/` directory and converts them into uniform, searchable chunks.

### Supported formats

| Format | Source file | Category assigned |
|--------|-------------|-------------------|
| `.pdf` | `it_security_policy.pdf` | `security` |
| `.txt` | `hr_policy.txt` | `hr` |
| `.txt` | `finance_report.txt` | `finance` |
| `.json` | `security_logs.json` | `security` |
| `.csv` | `employees.csv` | `employee` |

### Processing steps

1. **File discovery** — `load_documents()` scans `data/` and selects files by extension.
2. **Format parsing** — Dedicated loaders handle each type:
   - **PDF**: text extracted per page via `pypdf`.
   - **TXT**: read as plain text.
   - **CSV**: each row flattened to `key: value` pairs.
   - **JSON**: structured extraction of `events`, `employees`, `summary`, and `notes` fields.
3. **Category tagging** — Filename stem is mapped via `CATEGORY_MAP` to a logical domain (`hr`, `finance`, `security`, `employee`).
4. **Chunking** — Text is split into overlapping windows:
   - Chunk size: **400 characters**
   - Overlap: **50 characters**
   - Output: `DocumentChunk` objects with `chunk_id`, `content`, `source`, `category`, and `chunk_index`.

### Output

```python
DocumentChunk(
    chunk_id="hr_policy.txt::0",
    content="ACME CORPORATION — HUMAN RESOURCES POLICY...",
    source="hr_policy.txt",
    category="hr",
    chunk_index=0,
)
```

The ingestion layer is stateless and runs once at startup inside `EnterpriseRAG.initialize()`.

---

## 2. Embedding Layer

**Module:** `retriever.py` (`SemanticRetriever`)

The embedding layer converts text chunks and user queries into dense vector representations suitable for semantic similarity search.

### Model

| Property | Value |
|----------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Library | `sentence-transformers` (Hugging Face) |

### Index-time encoding

During `build_index()`:

1. All chunk `content` strings are passed to `SentenceTransformer.encode()`.
2. Vectors are cast to `float32` and **L2-normalized** via `faiss.normalize_L2()`.
3. Normalized vectors are added to the FAISS index.

### Query-time encoding

During `search()`:

1. The user query is encoded with the same model.
2. The query vector is L2-normalized.
3. Cosine similarity is computed as an inner product between normalized vectors.

### Design rationale

- **Same model for documents and queries** ensures vectors share the same semantic space.
- **L2 normalization** allows FAISS `IndexFlatIP` (inner product) to behave as cosine similarity.
- The model is small (~90 MB) and runs locally without an external API.

---

## 3. Vector Database

**Module:** `retriever.py` (FAISS index inside `SemanticRetriever`)

Embeddings are stored and queried using **FAISS** (Facebook AI Similarity Search).

### Index configuration

| Property | Value |
|----------|-------|
| Index type | `faiss.IndexFlatIP` (exact inner-product search) |
| Storage | In-memory (built at startup) |
| Metadata | Parallel `self.chunks` list maps FAISS row index → `DocumentChunk` |

### Search behavior

```python
allowed = set(get_accessible_categories(role))
retriever.search(query, top_k=3, allowed_categories=allowed)
```

1. Encode and normalize the query vector.
2. Retrieve `top_k × 15` nearest neighbors (over-fetch for RBAC filtering).
3. Filter results to categories the user's role is authorized to access.
4. Return the top 3 matches with confidence scores.

### Confidence score

The raw inner-product score from FAISS is clamped to `[0.0, 1.0]` and returned as `confidence_score`. Higher values indicate stronger semantic alignment between the query and the retrieved chunk.

### Trade-offs

| Choice | Benefit | Limitation |
|--------|---------|------------|
| `IndexFlatIP` | Exact, simple, no training | Linear scan — suitable for current corpus size |
| In-memory | Fast startup after first model load | Index rebuilt on every restart |
| RBAC category filter post-search | Single index, multi-source retrieval | Slightly more candidates scanned |

For production, the index could be persisted with `faiss.write_index()` and sharded by category.

---

## 4. Query Router

**Module:** `router.py`

The router classifies each user query into a document category **before** retrieval. The routed category is used for RBAC intent checks; search itself runs across all authorized sources.

### Categories

| Route | Target documents |
|-------|------------------|
| `hr` | `hr_policy.txt` |
| `finance` | `finance_report.txt` |
| `security` | `security_logs.json` |
| `employee` | `employees.csv` |

### Routing algorithm

`route_query()` uses **keyword scoring**:

1. Lowercase the query.
2. Count keyword hits per category from `ROUTE_KEYWORDS`.
3. Select the category with the highest hit count.
4. Compute route confidence as `best_score / total_score`.
5. Default to `hr` with confidence `0.3` when no keywords match.

### Example

```
Query:  "What was Sales revenue in Q3?"
Hits:   finance → ["revenue", "q3"]  (score: 2)
Result: category=finance, confidence=1.0
```

```
Query:  "Show me employee salary records"
Hits:   employee → ["salary", "employee record"]  (score: 2)
Result: category=employee, confidence=1.0
```

### Output

```python
RouteResult(
    category="finance",
    confidence=1.0,
    matched_keywords=["revenue", "q3"],
)
```

The routed category is checked by the RBAC layer. Retrieval uses `allowed_categories` from the user's role permissions.

---

## 5. RBAC Layer

**Module:** `rbac.py`

Role-Based Access Control enforces that users only retrieve documents they are authorized to see. RBAC runs **after routing** and **before** vector search.

### Roles

| Role | Description |
|------|-------------|
| `admin` | Full access to all document categories |
| `hr` | HR policies and employee records |
| `finance` | Financial reports only |
| `employee` | HR policies only (general staff access) |

### Permission matrix

```
                  ┌──────┬─────────┬──────────┬──────────┐
                  │  hr  │ finance │ security │ employee │
┌─────────────────┼──────┼─────────┼──────────┼──────────┤
│ admin           │  ✓   │    ✓    │    ✓     │    ✓     │
│ hr              │  ✓   │    ✗    │    ✗     │    ✓     │
│ finance         │  ✗   │    ✓    │    ✗     │    ✗     │
│ employee        │  ✓   │    ✗    │    ✗     │    ✗     │
└─────────────────┴──────┴─────────┴──────────┴──────────┘
```

### Enforcement flow

```
check_access(role, routed_category)
        │
        ├── allowed=True  → proceed to FAISS search
        │
        └── allowed=False → return denied response
                            (empty answer, access_granted=False)
```

### API

| Function | Purpose |
|----------|---------|
| `validate_role(role)` | Normalize and validate role string |
| `can_access(role, category)` | Boolean permission check |
| `check_access(role, category)` | Structured `AccessResult` with message |
| `enforce_access(role, category)` | Raises `RBACError` on denial |
| `get_accessible_categories(role)` | List all categories a role can query |

RBAC is checked against the **routed** category, not the source filename. A finance user asking about security logs is denied even if the router correctly identifies the intent as `security`.

---

## 6. Answer Generation

**Module:** `answer_generator.py` + `app.py` (response assembly)

Retrieval still uses FAISS, but answers are produced as **natural language** by `answer_generator.py`. The generator extracts structured facts from retrieved context and composes fluent sentences. No external API is required.

### Steps

1. **Retrieve** — FAISS returns the top 3 matching chunks across all RBAC-authorized categories.
2. **Merge context** — Chunk texts are deduplicated and combined into a context block.
3. **Confidence gate** — If the best retrieval score is below 0.35, return an unavailable message.
4. **Extract facts** — Domain-specific extractors pull relevant facts (parental leave, revenue, security events, etc.).
5. **Compose answer** — Facts are rewritten into complete, direct sentences that answer the question.
6. **Package** — `app.py` assembles the final `QueryResponse` with answer, source, and confidence.

### Response schema

```python
QueryResponse(
    query="What is the remote work policy?",
    role="employee",
    routed_category="hr",
    route_confidence=1.0,
    answer="Employees may work remotely up to 3 days per week with manager approval.",
    sources_used=["hr_policy.txt"],
    citations=[
        {"source": "hr_policy.txt", "excerpt": "...", "confidence": 0.6269}
    ],
    confidence_score=0.6269,
    access_granted=True,
    message="Answer generated from hr_policy.txt.",
)
```

### Confidence semantics

| Field | Meaning |
|-------|---------|
| `route_confidence` | How certain the router is about the query category |
| `confidence_score` | Semantic similarity between query and retrieved chunk |

### Unavailable information

When retrieval confidence is too low or the context does not contain the answer, the system returns:

```
The available documents do not contain this information.
```

Source and confidence are still included when a best match exists.

---

## Module Map

| Layer | Module | Key symbols |
|-------|--------|-------------|
| Orchestration | `app.py` | `EnterpriseRAG`, `QueryResponse` |
| Ingestion | `loader.py` | `load_documents()`, `DocumentChunk` |
| Embedding | `retriever.py` | `SemanticRetriever`, `SentenceTransformer` |
| Vector DB | `retriever.py` | `faiss.IndexFlatIP`, `search()` |
| Query Router | `router.py` | `route_query()`, `RouteResult` |
| RBAC | `rbac.py` | `check_access()`, `ROLE_PERMISSIONS` |
| Answer Generation | `answer_generator.py` | `AnswerGenerator`, `generate()` |

---

## Data Directory

```
data/
├── hr_policy.txt           → category: hr
├── finance_report.txt      → category: finance
├── security_logs.json      → category: security
├── it_security_policy.pdf  → category: security
└── employees.csv           → category: employee
```

---

## End-to-End Example

**Input:** `finance | What was the operating margin in Q3 2025?`

```
1. Router      → category=finance, confidence=1.0
2. RBAC        → role=finance, finance allowed ✓
3. Embedding   → query → 384-dim vector
4. FAISS       → search finance chunks → top hit from finance_report.txt
5. Answer Gen  → "Net profit reached $4.98 million, yielding an operating margin of 33.0%."
6. Response    → { answer, source: "finance_report.txt", confidence: 0.59 }
```

**Input:** `employee | Show me salary records`

```
1. Router      → category=employee, confidence=1.0
2. RBAC        → role=employee, employee denied ✗
3. Response    → { access_granted: false, answer: "" }
```

---

## Design Principles

1. **Modularity** — Each layer is a separate module with a single responsibility.
2. **Security before search** — RBAC gates access before any document content is returned.
3. **Domain-scoped retrieval** — Routing narrows the search space to the relevant corpus.
4. **Local-first** — Embeddings and search run entirely on-machine; no API keys required.
5. **Explainability** — Every answer includes source citations with excerpted evidence from retrieved chunks.
