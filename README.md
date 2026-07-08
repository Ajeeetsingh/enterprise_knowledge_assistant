# Enterprise Knowledge Assistant

Production-grade enterprise RAG platform: FastAPI backend, React frontend, PostgreSQL, document ingestion, hybrid retrieval, cross-encoder reranking, query intelligence, analytics, and admin tooling.

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest for development
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Manual testing

See **[docs/MANUAL_TESTING_GUIDE.md](docs/MANUAL_TESTING_GUIDE.md)** for Docker setup, demo users, and end-to-end checklists.

## Testing

```bash
cd backend
python -m pytest
```

See **[backend/TESTING.md](backend/TESTING.md)** for test layout and retrieval evaluation.

### Retrieval benchmark (144-case golden dataset)

```bash
cd backend
python -m app.evaluation.benchmark --label my_run --llm-provider none --no-compare
# or
python scripts/benchmark.py --retrieval --label my_run --llm-provider none --no-compare
```

See **[docs/EVALUATION_FRAMEWORK.md](docs/EVALUATION_FRAMEWORK.md)**.

## Production RAG Pipeline

```
Normalization → Structure Extraction → Semantic Chunking → Embeddings
  → Query Intelligence → Hybrid (Dense + BM25 + RRF) → Metadata Rescoring
  → Cross-Encoder Reranking → LLM
```

Architecture guides:

| Topic | Document |
|-------|----------|
| Ingestion pipeline | [docs/INGESTION_PIPELINE.md](docs/INGESTION_PIPELINE.md) |
| Retrieval pipeline | [docs/RETRIEVAL_PIPELINE.md](docs/RETRIEVAL_PIPELINE.md) |
| Evaluation framework | [docs/EVALUATION_FRAMEWORK.md](docs/EVALUATION_FRAMEWORK.md) |

## Architecture

- **[docs/02_system_architecture.md](docs/02_system_architecture.md)** — system design
- **[docs/05_testing_strategy.md](docs/05_testing_strategy.md)** — testing philosophy
- **[folder_structure.md](folder_structure.md)** — repository layout

## Legacy CLI

The Phase 00 prototype CLI still delegates to the backend RAG module:

```bash
python app.py
```

Production chat and APIs use `RagService` → `EnterpriseRAG` with the shared FAISS/BM25 index from document ingestion.

## Scripts

Backend operational scripts are documented in **[backend/scripts/README.md](backend/scripts/README.md)**.
