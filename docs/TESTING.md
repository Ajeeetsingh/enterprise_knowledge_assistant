# Testing

## Automated suites

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest
```

Covers API integration, auth/RBAC, document ACL, ingestion units, RAG units, analytics, and registration/role lifecycle tests.

### Frontend

```bash
cd frontend
npm install
npm test          # vitest
npm run build     # tsc -b && vite build
```

Covers pages, hooks, admin users, chat, documents, landing/register flows, and UI utilities.

## Manual application checklist

Use after seeding roles (and optionally demo data) per [DEVELOPMENT.md](DEVELOPMENT.md).

1. Open the landing page logged out → **Get Started** opens `/register`, **Sign In** opens `/login`.
2. Register a new user → login → confirm Employee navigation/permissions.
3. As Admin, open `/admin/users` → create a user with a selected role → change role → enable/disable.
4. Upload multiple documents → retry an identical file → expect “Already exists” (and highlight when the row is visible).
5. Ask a knowledge question → verify grounded answer and citations.
6. As a restricted role, confirm unauthorized documents are not returned.
7. Restart the backend → confirm Postgres data and (with volumes) storage/indexes survive.

### Demo accounts (development only)

Created only by explicit `--demo` / `--all` seeding. Password for demo users: see `scripts/seeding/demo_users.py` (`DemoPass1!`). Admin seed password: see `scripts/seeding/admin.py`.

| Email | Role | Notes |
|-------|------|-------|
| `admin@example.com` | Admin | From `--admin` |
| `hr@example.com` | HR | Demo |
| `finance@example.com` | Finance | Demo |
| `employee@example.com` | Employee | Demo |
| `quiet@example.com` | Employee | Quiet Employee **display name**; inactive-analytics fixture |

**Never** treat these as production defaults.

## Retrieval evaluation

Golden-dataset and benchmark tooling lives under `backend/app/evaluation/` and `backend/scripts/`.

```bash
cd backend
python -m app.evaluation.benchmark --label my_run --llm-provider none --no-compare
# or
python scripts/benchmark.py --retrieval --label my_run --llm-provider none --no-compare
```

Operational script notes: [backend/scripts/README.md](../backend/scripts/README.md).

## Legacy RAG CLI

```bash
python app.py
```

Delegates to `python -m app.rag.cli` inside `backend`. Useful for offline RAG experiments; the product UI uses the HTTP API.
