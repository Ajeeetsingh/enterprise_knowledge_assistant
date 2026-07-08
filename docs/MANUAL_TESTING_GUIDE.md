# Manual Testing Guide

This guide walks you through running and testing the **full Enterprise Knowledge Assistant** locally — from the original RAG pipeline to the web application with auth, documents, chat, admin portal, analytics, and reporting.

---

## What you are testing

The repository contains three related layers:

| Layer | Purpose | How to run |
|-------|---------|------------|
| **Legacy RAG CLI** | Original prototype (`role \| question`) | `python app.py` |
| **Automated tests** | Regression safety net | `backend`: `pytest` · `frontend`: `npm test` |
| **Full web application** | Production-style UI + API + DB | Postgres + backend + frontend (this guide) |

The root `README.md` focuses on the legacy CLI. Use **this document** for the full application.

---

## Prerequisites

- **Docker Desktop** (for PostgreSQL)
- **Python 3.12+** with `backend/requirements.txt` installed
- **Node.js 20+** with `frontend` dependencies (`npm install`)
- **~500 MB free disk** (PostgreSQL + embedding model on first chat/upload)

---

## One-time setup

### 1. Environment files

**Project root `.env`** (copy from `.env.example`):

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/eka
JWT_SECRET=dev-secret-change-me
```

**`frontend/.env`** (copy from `frontend/.env.example`):

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SHOW_TEST_USERS=true
VITE_TEST_USER_LABEL=Admin
VITE_TEST_USER_EMAIL=admin@example.com
```

### 2. Start PostgreSQL

```powershell
docker compose up postgres -d
```

### 3. Migrate the database

```powershell
cd backend
alembic upgrade head
cd ..
```

### 4. Seed roles, users, and demo data

**Option A — one command (recommended):**

```powershell
python scripts/setup_manual_testing.py
```

**Option B — step by step:**

```powershell
python scripts/seed_database.py --roles
python scripts/seed_database.py --admin
python scripts/seed_database.py --demo
```

Or combine flags:

```powershell
python scripts/seed_database.py --all
```

**Faster seed (skip RAG chat / embedding model download):**

```powershell
python scripts/setup_manual_testing.py --skip-chat
```

**Analytics audit events only (no uploads):**

```powershell
python scripts/seed_database.py --demo --analytics-only
```

> The first run **with chat** downloads the sentence-transformers model (~90 MB) and builds the FAISS index. Expect several minutes on a slow connection.

---

## Test accounts

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| `admin@example.com` | `AdminPass1!` | Admin | Full access, admin portal, analytics |
| `hr@example.com` | `DemoPass1!` | HR | HR documents + employee records |
| `finance@example.com` | `DemoPass1!` | Finance | Finance documents |
| `employee@example.com` | `DemoPass1!` | Employee | Limited access (HR only) |
| `quiet@example.com` | `DemoPass1!` | Employee | No seeded activity — useful for “inactive user” analytics |

---

## Start the application

**Terminal 1 — Backend:**

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**

```powershell
cd frontend
npm run dev
```

**Sanity checks:**

| URL | Expected |
|-----|----------|
| http://localhost:5173 | Frontend home |
| http://localhost:8000/health | `{"status":"healthy"}` |
| http://localhost:8000/docs | Swagger UI (all APIs) |

---

## Golden-path walkthrough (~30 minutes)

Follow this sequence once to exercise the core product flow.

### 1. Authentication

1. Open http://localhost:5173/login
2. Sign in as **admin@example.com** / **AdminPass1!**
3. Confirm redirect to `/dashboard`
4. Refresh the page — session should persist
5. Log out; try visiting `/chat` — should redirect to login
6. Wrong password → “Invalid email or password”

### 2. Knowledge base (documents)

Sample files are seeded from `backend/tests/fixtures/sample_docs/` when you run `seed_database.py --demo`.

**Verify as admin:**

1. `/admin/uploads` — upload an extra TXT or PDF file
2. `/admin/documents` — confirm status becomes searchable/indexed
3. `/documents` — same documents from the employee-facing view

### 3. Chat & conversations (RAG)

1. Go to `/chat`
2. Ask questions grounded in uploaded docs, for example:
   - “What is the parental leave policy?”
   - “What are the password requirements?”
   - “What is the remote work policy?”
3. Verify: answer text, citations, confidence score
4. Start a **new conversation** and ask a follow-up
5. Reload `/chat` — conversation history should persist

### 4. RBAC (role-based access)

Use **separate browser profiles or incognito windows** for each role.

| Test | User | Expected |
|------|------|----------|
| Admin sees all admin routes | admin | `/admin/*` accessible |
| HR chat on HR topics | hr | Answers from HR policies |
| Finance chat on finance topics | finance | Answers from finance reports |
| Employee blocked from finance | employee | Finance questions denied or empty retrieval |
| Non-admin blocked from admin | employee | Redirect from `/admin` |

### 5. Admin portal

Visit each item in the admin sidebar:

| Route | What to verify |
|-------|----------------|
| `/admin` | Loads (metrics are **placeholders** — not live yet) |
| `/admin/documents` | List, detail, lifecycle states |
| `/admin/uploads` | Upload pipeline |
| `/admin/users` | Create, edit, deactivate users |
| `/admin/collections` | Collection management |

### 6. Monitoring

Two separate areas:

- **`/monitoring`** — operational summary (Phase 7)
- **`/admin/analytics/monitoring`** — analytics dashboard (Phase 11)

Both should load after you have used the app.

### 7. Analytics dashboards

After running `seed_database.py --demo` (or generating activity manually):

| Route | Content |
|-------|---------|
| `/admin/analytics` | User adoption, DAU/WAU, top users |
| `/admin/analytics/ai` | Questions, responses, retrieval quality |
| `/admin/analytics/knowledge` | Document usage, searches, freshness |
| `/admin/analytics/monitoring` | Health, performance, resources |
| `/admin/analytics/errors` | Failures, categories, endpoints |

Try each **date filter**: Today, Last 7/30/90 Days, Custom Range. Click **Refresh**.

### 8. Reporting & export

From any analytics page → **Export**, or go to `/admin/reports`:

1. Choose module, date range, and format (CSV / Excel / PDF)
2. Download and open the file
3. Confirm KPIs, tables, and trends match the dashboard

---

## Full feature checklist

Use this as a tick sheet during a thorough test pass.

### Authentication & sessions

- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Token refresh on API calls (stay logged in after idle)
- [ ] Logout clears session
- [ ] Protected routes redirect unauthenticated users

### Users & roles

- [ ] Admin creates a new user in `/admin/users`
- [ ] Assign HR / Finance / Employee role
- [ ] Deactivate user — login blocked
- [ ] `/users` page (non-admin layout) for admin user management

### Documents

- [ ] Upload TXT, CSV, JSON
- [ ] Upload PDF (if available)
- [ ] Document appears with correct filename and status
- [ ] Delete document
- [ ] Re-upload duplicate — handled gracefully

### Chat & RAG

- [ ] Question with good document match → cited answer
- [ ] Question with no match → graceful empty/failure message
- [ ] Multiple conversations
- [ ] Conversation persists after reload
- [ ] RBAC: role-appropriate access to document categories

### Admin portal

- [ ] All sidebar links work
- [ ] Uploads page processes files
- [ ] User CRUD
- [ ] Collections page

### Monitoring & analytics

- [ ] `/monitoring` summary loads
- [ ] All five analytics dashboards load with data
- [ ] Date filters change displayed metrics
- [ ] Export CSV from dashboard
- [ ] Export Excel from dashboard
- [ ] Export PDF from dashboard
- [ ] `/admin/reports` standalone export page

### API (Swagger)

- [ ] `POST /api/v1/auth/login`
- [ ] `GET /api/v1/auth/me` with Bearer token
- [ ] `POST /api/v1/documents/upload`
- [ ] `POST /api/v1/chat/ask`
- [ ] `GET /api/v1/admin/analytics/users/overview`
- [ ] `POST /api/v1/admin/reports/export`

---

## Generating analytics data manually

If dashboards look empty, perform these actions then refresh analytics:

1. Log in/out as several users
2. Upload 5–10 documents via `/admin/uploads`
3. Ask 15–20 chat questions (include some with no matching docs)
4. Fail a login (wrong password)
5. Create a new user and assign roles

Or re-run:

```powershell
python scripts/seed_database.py --demo
```

---

## Legacy RAG CLI (optional)

The original prototype still works independently of the web app:

```powershell
python app.py
```

Interactive format:

```
admin | What are the password requirements?
hr | What is the parental leave policy?
quit
```

Automated regression tests:

```powershell
cd backend
python -m pytest
python -m app.evaluation.benchmark --label manual_check --llm-provider none --no-compare
```

---

## Automated regression suites

Run before and after manual testing:

```powershell
# Backend (~879 tests)
cd backend
python -m pytest

# Frontend (~118 tests)
cd frontend
npm test
```

See [backend/TESTING.md](../backend/TESTING.md) for backend test details.

---

## Known placeholders

Do not treat these as bugs:

- **`/dashboard`** — placeholder (“future phase”)
- **`/admin` dashboard** — mock metrics, not wired to live analytics
- **Audit log UI** — backend audit API exists; no dedicated frontend page yet

Live analytics live under **`/admin/analytics/*`**.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `connection refused` on login | Backend not running on port 8000 |
| CORS errors | Confirm `VITE_API_BASE_URL=http://localhost:8000/api/v1` |
| Database connection failed | `docker compose up postgres -d` and check `DATABASE_URL` uses `localhost` |
| Chat returns 503 | No searchable documents — run `seed_database.py --demo` or upload files |
| Slow first chat/upload | Embedding model downloading — wait or use `--skip-chat` for seed |
| Analytics empty | Run `seed_database.py --demo` or generate activity (see above) |
| Admin analytics 403 | Must log in as Admin (`admin@example.com`) |

---

## Suggested 2-hour full tour

| Time | Activity |
|------|----------|
| 0:00–0:15 | Docker, migrate, `setup_manual_testing.py`, start servers |
| 0:15–0:30 | Login flows, all test accounts |
| 0:30–0:50 | Documents upload + admin document management |
| 0:50–1:10 | Chat + conversations as admin and employee |
| 1:10–1:30 | RBAC matrix (HR, Finance, Employee) |
| 1:30–1:45 | Admin portal (users, uploads, collections) |
| 1:45–2:00 | Analytics dashboards + export reports |

---

## Script reference

| Script | Purpose |
|--------|---------|
| `scripts/seed_database.py` | Unified seeder (`--roles`, `--admin`, `--demo`, `--all`) |
| `scripts/setup_manual_testing.py` | Runs `seed_database.py --all` |
