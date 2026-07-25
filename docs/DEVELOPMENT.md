# Development

Local setup for engineers working on Knowra.

Product and architecture context: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) · [ARCHITECTURE.md](ARCHITECTURE.md).  
Production deploy steps: [DEPLOYMENT.md](DEPLOYMENT.md) (do not use this file for production hosting).

## Prerequisites

- Python **3.12+**
- Node.js **20+**
- Docker Desktop (PostgreSQL via Compose)
- Disk for embedding/reranker model downloads on first use (~hundreds of MB)

## Clone and environment

```bash
git clone <repository-url>
cd enterprise_knowledge_assistant

cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit `.env`:

- `DATABASE_URL` - for host-run backend talking to Compose Postgres, use `localhost:5432`
- `JWT_SECRET` - any non-empty value is fine in `APP_ENV=development`
- `GROQ_API_KEY` (or another LLM provider) when you want live answers

Edit `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Optional login hints (development only):

```env
VITE_SHOW_TEST_USERS=true
VITE_TEST_USER_LABEL=Admin
VITE_TEST_USER_EMAIL=admin@example.com
```

Never put real passwords in committed env files.

## Database

Start Postgres:

```bash
docker compose up postgres -d
```

Apply migrations:

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
alembic upgrade head
```

### Bootstrap (required for a usable app)

```bash
# from repository root
python scripts/seed_database.py --roles
python scripts/seed_database.py --admin
```

This creates system roles and a local admin (`admin@example.com`). **These credentials are for local development only.** Production bootstrap is documented in [DEPLOYMENT.md](DEPLOYMENT.md).

### Optional demo data

```bash
python scripts/seed_database.py --demo
# or everything:
python scripts/seed_database.py --all
```

Convenience wrapper used by the manual checklist:

```bash
python scripts/setup_manual_testing.py
```

Demo accounts (password `DemoPass1!`) include HR, Finance, Employee, and Quiet Employee (`quiet@example.com`) — an **Employee** user with no seeded activity for analytics tests. Demo seeding is never automatic on application start. Account table: [TESTING.md](TESTING.md).

## Run the app

Terminal 1 - API:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - UI:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health

## Common commands

| Task | Command |
|------|---------|
| Backend tests | `cd backend && python -m pytest` |
| Frontend tests | `cd frontend && npm test` |
| Typecheck + build | `cd frontend && npm run build` |
| Seed roles/admin/demo | `python scripts/seed_database.py --roles\|--admin\|--demo\|--all` |
| Legacy RAG CLI | `python app.py` (delegates to `python -m app.rag.cli` in `backend`) |

## Project layout (summary)

```
backend/app/          FastAPI application (api, auth, ingestion, rag, services)
backend/alembic/      Schema migrations
frontend/src/         React application (pages, features, layouts)
scripts/              Seeding and local setup helpers
docs/                 PROJECT_OVERVIEW, architecture, development, deployment, testing
docker-compose.yml    Local development Postgres (+ optional backend)
```

Production Compose layout and volumes: [DEPLOYMENT.md](DEPLOYMENT.md).

## Public registration (local)

With roles seeded, open `/register`, create an account, then sign in. The backend always assigns **Employee**. Promote users from `/admin/users`.

## Local notes

- `docker-compose.yml` forces `APP_ENV=development` and publishes Postgres — local work only.
- Dev-only UI routes (`/auth-debug`, `/design-system`, …) are stripped from production builds.
- Multi-worker / production rate-limiting and other host constraints: see [DEPLOYMENT.md](DEPLOYMENT.md#known-deployment-limitations) and [PROJECT_OVERVIEW.md §19](PROJECT_OVERVIEW.md#19-known-limitations).
