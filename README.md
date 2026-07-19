# Enterprise Knowledge Assistant

An AI-powered enterprise knowledge platform that turns organisational documents into a secure, searchable knowledge base — so employees can ask natural-language questions and receive grounded answers with citations.

This repository is a **production-oriented portfolio / single-organisation demo**: a complete FastAPI + React application with ingestion, hybrid retrieval, role-aware RAG, and admin tooling. It is designed to be cloned, configured, run, tested, and deployed by another engineer.

---

## The problem

In most organisations, knowledge is scattered across PDFs, handbooks, policies, and shared drives. Employees waste time hunting for answers, the same questions are asked repeatedly, and generic AI tools risk surfacing information that a given person should not see.

## The solution

Enterprise Knowledge Assistant ingests documents, builds a hybrid search index, and answers questions with retrieved evidence — while **backend authorization** decides what each user may see.

```
Upload → parse → normalize → structure → semantic chunks
  → embeddings + BM25 → hybrid retrieval → rerank
  → ACL filter (fail-closed) → LLM answer → citations
```

## Who it is for

- Enterprises with large internal document collections  
- HR, Finance, Operations, and compliance-heavy teams  
- Internal knowledge-management and enablement groups  
- Engineers evaluating secure RAG architectures  

This project does **not** claim existing commercial customers.

## Benefits

- Faster discovery of policies and procedures  
- Answers tied to source citations  
- Less manual folder searching  
- Centralised knowledge access in the browser  
- Role-aware retrieval and document ACLs  
- Multi-file upload with duplicate detection  
- Admin tooling for users, documents, and analytics  

## Key features

| Area | Capabilities |
|------|----------------|
| Q&A | Conversational chat, suggested questions, cited answers |
| Retrieval | Dense (FAISS) + sparse (BM25) hybrid search, query intelligence, cross-encoder reranking |
| Documents | Multi-file upload, processing pipeline, duplicate prevention, viewer |
| Security | JWT auth, RBAC (Admin / HR / Finance / Employee), document ACL, fail-closed RAG filtering, upload validation, rate limiting |
| Identity | Public registration (always Employee), Admin atomic user create + runtime role changes, last-admin lockout protection |
| Ops | Dashboard, admin portal, analytics, monitoring hooks, Docker Compose |

Only features that exist in this codebase are listed above.

## Security model (concise)

- Permissions are enforced on the **backend** on every request (roles loaded from the database).  
- Document visibility / allowed roles / ownership gate both direct document APIs and RAG evidence.  
- Public `/auth/register` cannot choose a privileged role.  
- Production startup rejects the placeholder `JWT_SECRET`.  
- Demo users are created **only** when seeding is invoked explicitly.

No compliance certifications are claimed.

## Architecture

| Layer | Stack |
|-------|--------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python |
| Database | PostgreSQL |
| Retrieval | FAISS + BM25 + embeddings + CrossEncoder |
| LLM | Configurable (e.g. Groq) |
| Deploy | Docker Compose |

Deep dive: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Roles

| Role | How obtained |
|------|----------------|
| **Employee** | Default for public self-registration |
| **HR** / **Finance** / **Admin** | Assigned by an Admin (or explicit seed scripts in development) |

Backend authorization — not the UI — controls access.

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

Open http://localhost:5173 — full details in **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

## Demo data

Optional fictional users and sample activity can be seeded for local demos:

```bash
python scripts/seed_database.py --demo
```

Demo data is **synthetic** and intended only for development/testing. Application startup never creates demo credentials automatically. Account tables and warnings: **[docs/TESTING.md](docs/TESTING.md)**.

## Testing

The project includes backend, frontend, RBAC, retrieval, and integration tests.

```bash
cd backend && python -m pytest
cd frontend && npm test && npm run build
```

See **[docs/TESTING.md](docs/TESTING.md)**.

## Deployment

For a public or VPS-style host: set `APP_ENV=production`, a strong `JWT_SECRET`, private Postgres, and use `docker-compose.prod.yml` for the API + database. Build the frontend with the correct `VITE_API_BASE_URL`.

Guide: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

## Project status

Production-oriented **portfolio / single-tenant demo** implementation.

Known limitations intentionally deferred:

- Single-organisation model (`TENANT_ID`)  
- In-memory rate limiting (single-process)  
- Local FAISS persistence (not a managed vector service)  
- No enterprise SSO / IdP  

## Documentation

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, pipelines, security |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, seeding, commands |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production config, Docker, checklist |
| [TESTING.md](docs/TESTING.md) | Automated + manual testing |

## License

No `LICENSE` file is present in this repository. Clarify licensing with the author before commercial reuse.
