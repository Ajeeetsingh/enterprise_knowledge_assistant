# Knowra

An AI-powered enterprise knowledge platform that turns organisational documents into a secure, searchable knowledge base, so employees can ask natural-language questions and receive grounded answers with citations.

This repository is a **production-oriented portfolio / single-organisation demo**: a complete FastAPI + React application with ingestion, hybrid retrieval, role-aware RAG, and admin tooling. It is designed to be cloned, configured, run, tested, and deployed by another engineer.

For a full product and system explanation, read **[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)**.

---

## The problem

In most organisations, knowledge is scattered across PDFs, handbooks, policies, and shared drives. Employees waste time hunting for answers, the same questions are asked repeatedly, and generic AI tools risk surfacing information that a given person should not see.

## The solution

Knowra ingests documents, builds a hybrid search index, and answers questions with retrieved evidence — while **backend authorization** decides what each user may see.

```
Upload → parse → chunk → embeddings + BM25
  → hybrid retrieval → rerank → ACL filter (fail-closed)
  → LLM answer → citations (open source → page → highlight)
```

## Who it is for

- Enterprises with large internal document collections  
- HR, Finance, Operations, and compliance-heavy teams  
- Internal knowledge-management and enablement groups  
- Engineers evaluating secure RAG architectures  

This project does **not** claim existing commercial customers.

## Benefits

- Faster discovery of policies and procedures  
- Answers tied to source citations and openable source passages  
- Role-aware retrieval and document ACLs  
- Multi-file upload with duplicate detection  
- Admin tooling for users, documents, analytics, and monitoring  

## Key features

| Area | Capabilities |
|------|----------------|
| Q&A | Conversational chat, suggested questions, cited answers, source open + page highlight |
| Retrieval | Dense (FAISS) + sparse (BM25) hybrid search, query intelligence, cross-encoder reranking |
| Documents | Multi-file upload, processing pipeline, duplicate prevention, viewer |
| Security | JWT auth, RBAC (Admin / HR / Finance / Employee), document ACL, fail-closed RAG filtering, rate limiting |
| Identity | Public registration (always Employee), Admin user create + runtime role changes, last-admin protection |
| Ops | Dashboard, admin portal, analytics, monitoring, Docker Compose |

Only features that exist in this codebase are listed above. Details: **[PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)**.

## Architecture (summary)

| Layer | Stack |
|-------|--------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python |
| Database | PostgreSQL |
| Retrieval | FAISS + BM25 + embeddings + CrossEncoder |
| LLM | Configurable (e.g. Groq) |
| Deploy | Docker Compose |

Deep dive: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** · Full product context: **[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)**

## Roles (summary)

| Role | How obtained |
|------|----------------|
| **Employee** | Default for public self-registration |
| **HR** / **Finance** / **Admin** | Assigned by an Admin (or explicit seed scripts in development) |

Backend authorization — not the UI — controls access. Permission matrix: **[PROJECT_OVERVIEW.md §4](docs/PROJECT_OVERVIEW.md#4-user-roles-and-access-model)**.

## Quick start

**Prerequisites:** Python 3.12+, Node 20+, Docker (Postgres).

```bash
git clone <repository-url>
cd enterprise_knowledge_assistant
cp .env.example .env
cp frontend/.env.example frontend/.env

docker compose up postgres -d

cd backend
pip install -r requirements.txt
alembic upgrade head
cd ..

python scripts/seed_database.py --roles
python scripts/seed_database.py --admin

cd backend && uvicorn app.main:app --reload --port 8000
# new terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — full local workflow in **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

## Demo data

Optional fictional users and sample activity:

```bash
python scripts/seed_database.py --demo
```

Demo data is **synthetic** and for development/testing only. Startup never creates demo credentials automatically. Accounts: **[docs/TESTING.md](docs/TESTING.md)**.

## Testing

```bash
cd backend && python -m pytest
cd frontend && npm test && npm run build
```

See **[docs/TESTING.md](docs/TESTING.md)**.

## Deployment

Production hosting uses `APP_ENV=production`, a strong `JWT_SECRET`, private Postgres, and `docker-compose.prod.yml` for the API and database. Build the frontend with the correct `VITE_API_BASE_URL`.

**Instructions:** **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**  
**Limitations of this release:** **[PROJECT_OVERVIEW.md §19](docs/PROJECT_OVERVIEW.md#19-known-limitations)** and [DEPLOYMENT.md](docs/DEPLOYMENT.md#known-deployment-limitations).

## Documentation

| Document | Contents |
|----------|----------|
| [PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Complete product & system reference |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture and pipelines |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, seeding, commands |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production configuration and Docker |
| [TESTING.md](docs/TESTING.md) | Automated + manual testing |

## License

No `LICENSE` file is present in this repository. Clarify licensing with the author before commercial reuse.
