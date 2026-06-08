# Enterprise RAG Intelligence Challenge

A modular retrieval-augmented generation (RAG) system for querying enterprise documents with role-based access control. The pipeline ingests HR policies, finance reports, security logs, employee records, and IT security policies, then returns cited answers grounded in retrieved context.

## Features

- **PDF/TXT/CSV/JSON ingestion** — automatic document loading and chunking from `data/`
- **Semantic retrieval using FAISS** — `all-MiniLM-L6-v2` embeddings with cosine similarity search
- **Query-aware routing** — keyword-based intent classification into HR, finance, security, and employee domains
- **RBAC enforcement** — four roles (`admin`, `hr`, `finance`, `employee`) with per-category access rules
- **Cross-source retrieval** — top 3 chunks retrieved across all authorized document sources
- **Explainable answers with citations** — each response includes source filenames and excerpted evidence
- **Confidence scoring** — retrieval similarity score (0–1) on every answer
- **Automated test suite** — 37/37 passing (`python test_pipeline.py`)

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the demo
python app.py

# 4. Run the test suite
python test_pipeline.py
```

The first run downloads the embedding model (~90 MB) from Hugging Face.

## Project Structure

```
RAG_Pipeline/
├── app.py                 # Main application and CLI
├── answer_generator.py    # Natural-language answer composition
├── loader.py              # Document ingestion (PDF, TXT, CSV, JSON)
├── retriever.py           # FAISS semantic search
├── router.py              # Query intent routing
├── rbac.py                # Role-based access control
├── test_pipeline.py       # Automated test suite
├── requirements.txt
├── architecture.md        # Detailed system design
└── data/
    ├── hr_policy.txt
    ├── finance_report.txt
    ├── security_logs.json
    ├── it_security_policy.pdf
    └── employees.csv
```

## How It Works

```
User Query + Role
       │
       ▼
  Query Router ──► category (hr / finance / security / employee)
       │
       ▼
  RBAC Check ──► allow or deny
       │
       ▼
  FAISS Retrieval ──► top 3 chunks from authorized sources
       │
       ▼
  Answer Generator ──► natural-language answer + citations
```

1. **Ingest** — documents are parsed, tagged by category, and split into 400-character overlapping chunks
2. **Route** — the query is classified by keyword scoring (security keywords take priority on ties)
3. **Authorize** — RBAC checks whether the user's role may access the routed category
4. **Retrieve** — FAISS returns the 3 most semantically similar chunks from all permitted sources
5. **Answer** — context is synthesized into a direct response with source citations and confidence score

## Usage

### Interactive CLI

After running `python app.py`, enter queries as:

```
<role> | <question>
```

Examples:

```
hr | What is the parental leave policy?
finance | What was Q3 revenue for the Sales department?
admin | What are the password requirements?
admin | Were there any malware incidents?
employee | What is the remote work policy?
```

Type `quit` to exit.

### Programmatic API

```python
from app import EnterpriseRAG

rag = EnterpriseRAG()
rag.initialize()

response = rag.query("What are the password requirements?", role="admin")

print(response.answer)
print(response.sources_used)
print(response.citations)
print(response.confidence_score)
print(response.access_granted)
```

### Response Format

```json
{
  "query": "What are the password requirements?",
  "role": "admin",
  "routed_category": "security",
  "route_confidence": 1.0,
  "answer": "Employees must use passwords of at least 14 characters with mixed character types. Passwords must be changed every 90 days.",
  "sources_used": ["it_security_policy.pdf", "security_logs.json"],
  "citations": [
    {
      "source": "it_security_policy.pdf",
      "excerpt": "ACME CORPORATION - IT SECURITY POLICY Document ID: SEC-POL-2025-002...",
      "confidence": 0.6096
    }
  ],
  "confidence_score": 0.6096,
  "access_granted": true,
  "message": "Answer generated from it_security_policy.pdf, security_logs.json."
}
```

## RBAC Matrix

| Role | HR | Finance | Security | Employee Records |
|------|:--:|:-------:|:--------:|:----------------:|
| admin | Yes | Yes | Yes | Yes |
| hr | Yes | No | No | Yes |
| finance | No | Yes | No | No |
| employee | Yes | No | No | No |

Access is denied before retrieval when a role cannot view the routed document category.

## Supported Document Formats

| Format | Loader | Example File | Category |
|--------|--------|--------------|----------|
| PDF | `pypdf` text extraction | `it_security_policy.pdf` | security |
| TXT | plain text read | `hr_policy.txt` | hr |
| TXT | plain text read | `finance_report.txt` | finance |
| JSON | structured field parsing | `security_logs.json` | security |
| CSV | row flattening | `employees.csv` | employee |

Add new files to `data/` and map the filename stem in `CATEGORY_MAP` inside `loader.py`.

## Testing

```bash
python test_pipeline.py
```

The suite covers:

- **Ingestion** — all 5 files load, PDF chunks exist, category mapping
- **Routing** — HR, finance, security, employee, and security keyword queries
- **RBAC** — allow/deny matrix and per-role category lists
- **End-to-end** — 11 full pipeline queries including PDF, multi-source, and access denials

Results are written to `results/test_results.json` and `results/test_results.txt`.

The enterprise test suite (`realistic_enterprise_test.py`) writes to the same `results/` folder.

## Configuration

| Setting | Location | Default |
|---------|----------|---------|
| Chunk size | `loader.py` | 400 characters |
| Chunk overlap | `loader.py` | 50 characters |
| Embedding model | `retriever.py` | `all-MiniLM-L6-v2` |
| Top-K retrieval | `app.py` | 3 chunks |
| Confidence threshold | `answer_generator.py` | 0.35 |
| Data directory | `app.py` | `./data` |

## Dependencies

- `sentence-transformers` — embedding model
- `faiss-cpu` — vector similarity search
- `pypdf` — PDF text extraction
- `torch`, `numpy` — model runtime

## Architecture

See [architecture.md](architecture.md) for layer-by-layer design documentation including ingestion, embedding, FAISS indexing, query routing, RBAC, and answer generation.

## Extending

- **New documents** — add files to `data/` and update `CATEGORY_MAP` in `loader.py`
- **New roles** — update `ROLE_PERMISSIONS` in `rbac.py`
- **New routing keywords** — update `ROUTE_KEYWORDS` in `router.py`
- **Persisted index** — use `faiss.write_index()` / `faiss.read_index()` for faster startup
- **LLM answers** — replace `AnswerGenerator` with an external model call; retrieval and RBAC layers stay the same
