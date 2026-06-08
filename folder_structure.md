# Enterprise Knowledge Assistant — Folder Structure

Target architecture for converting the RAG prototype into a single-tenant, monolithic MVP with a clear path to SaaS.

**Product:** Enterprise Knowledge Assistant  
**Architecture:** Monolith (FastAPI + React + PostgreSQL)  
**Status:** Prototype migrated — Phase 1 backend foundation in place

---

## 1. Complete Folder Tree

```
enterprise-knowledge-assistant/
│
├── README.md
├── docker-compose.yml                 # Postgres + backend + frontend (dev)
├── .env.example
├── .gitignore
│
├── docs/
│   ├── architecture.md                # System design and data flows
│   ├── api.md                         # OpenAPI notes / conventions
│   ├── rbac-matrix.md                 # Role and permission matrix
│   └── adr/                           # Architecture decision records
│       └── 001-monolith-mvp.md
│
├── backend/
│   ├── pyproject.toml                 # or requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory, lifespan, CORS
│   │   ├── config.py                  # Settings (env, JWT, paths, model names)
│   │   ├── dependencies.py            # DI: DB session, current user, services
│   │   │
│   │   ├── api/                       # HTTP layer — thin controllers
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # Aggregates all route modules
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py            # POST /login, POST /refresh, GET /me
│   │   │       ├── documents.py       # upload, list, delete, reindex
│   │   │       ├── chat.py            # conversations, messages, query
│   │   │       ├── audit.py           # audit log queries (admin)
│   │   │       └── health.py          # /health, /ready
│   │   │
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── chat.py
│   │   │   └── audit.py
│   │   │
│   │   ├── services/                  # Business orchestration
│   │   │   ├── auth_service.py
│   │   │   ├── document_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── rag_service.py         # Wraps RAG engine for API use
│   │   │   └── audit_service.py
│   │   │
│   │   ├── rag/                       # RAG engine (domain core)
│   │   │   ├── __init__.py
│   │   │   ├── engine.py              # Orchestrator (from prototype app.py)
│   │   │   ├── router.py              # Query routing
│   │   │   ├── retriever.py           # FAISS + embeddings
│   │   │   ├── answer_generator.py
│   │   │   ├── rbac.py                # Category-level RBAC
│   │   │   ├── types.py               # Citation, QueryResponse, RetrievalResult
│   │   │   └── index_manager.py       # Build/rebuild/load FAISS index
│   │   │
│   │   ├── ingestion/                 # Document processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── loader.py              # PDF/TXT/CSV/JSON parsers
│   │   │   ├── chunker.py             # Text splitting (from prototype loader)
│   │   │   ├── categorizer.py         # Filename/metadata → category mapping
│   │   │   ├── pipeline.py            # ingest(file) → chunks → persist metadata
│   │   │   └── supported_types.py     # MIME/extension registry
│   │   │
│   │   ├── auth/                      # Authentication module
│   │   │   ├── __init__.py
│   │   │   ├── jwt.py                 # Create/verify tokens
│   │   │   ├── password.py            # Hash/verify (bcrypt)
│   │   │   ├── roles.py               # Role enum + helpers
│   │   │   └── security.py            # FastAPI auth dependencies
│   │   │
│   │   ├── rbac/                      # Authorization (beyond JWT role)
│   │   │   ├── __init__.py
│   │   │   ├── permissions.py         # Document + category rules
│   │   │   ├── policy.py              # can_access(user, resource)
│   │   │   └── document_acl.py        # Document-level permissions
│   │   │
│   │   ├── audit/                     # Audit logging module
│   │   │   ├── __init__.py
│   │   │   ├── logger.py              # write_audit_event()
│   │   │   ├── events.py              # Event type constants
│   │   │   └── middleware.py          # Optional request-level hooks
│   │   │
│   │   ├── db/                        # Database module
│   │   │   ├── __init__.py
│   │   │   ├── session.py             # SQLAlchemy engine + session
│   │   │   ├── base.py                # Declarative base
│   │   │   ├── models/
│   │   │   │   ├── user.py
│   │   │   │   ├── document.py
│   │   │   │   ├── document_chunk.py
│   │   │   │   ├── conversation.py
│   │   │   │   ├── message.py
│   │   │   │   ├── audit_log.py
│   │   │   │   └── document_permission.py
│   │   │   └── repositories/
│   │   │       ├── user_repo.py
│   │   │       ├── document_repo.py
│   │   │       ├── chat_repo.py
│   │   │       └── audit_repo.py
│   │   │
│   │   ├── storage/                   # File storage abstraction
│   │   │   ├── __init__.py
│   │   │   ├── local.py               # MVP: filesystem under storage/documents/
│   │   │   └── interface.py           # Future: S3, SharePoint adapter
│   │   │
│   │   ├── integrations/              # Future external connectors (stubs in MVP)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Connector interface
│   │   │   ├── slack/                 # Phase 2
│   │   │   ├── teams/                 # Phase 2
│   │   │   └── sharepoint/            # Phase 2
│   │   │
│   │   └── core/                      # Shared utilities
│   │       ├── exceptions.py
│   │       ├── logging.py
│   │       └── tenancy.py             # tenant_id placeholder (single-tenant MVP)
│   │
│   ├── storage/                       # Runtime data (gitignored)
│   │   ├── documents/                 # Uploaded raw files
│   │   └── indexes/                   # FAISS index + metadata JSON
│   │
│   └── tests/
│       ├── unit/
│       │   ├── test_router.py
│       │   ├── test_rbac.py
│       │   └── test_answer_generator.py
│       ├── integration/
│       │   ├── test_auth_api.py
│       │   ├── test_documents_api.py
│       │   └── test_chat_api.py
│       ├── rag/
│       │   ├── test_pipeline.py
│       │   └── realistic_enterprise_test.py
│       └── fixtures/
│           └── sample_docs/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── api/                       # Axios/fetch clients
│       │   ├── client.ts              # JWT interceptor
│       │   ├── auth.ts
│       │   ├── documents.ts
│       │   ├── chat.ts
│       │   └── audit.ts
│       │
│       ├── auth/                      # Auth state + guards
│       │   ├── AuthContext.tsx
│       │   ├── useAuth.ts
│       │   └── ProtectedRoute.tsx
│       │
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── ChatPage.tsx           # Knowledge Assistant
│       │   ├── DocumentsPage.tsx      # Upload / list / delete
│       │   └── AuditPage.tsx          # Admin only
│       │
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatWindow.tsx
│       │   │   ├── MessageList.tsx
│       │   │   ├── CitationPanel.tsx
│       │   │   └── ConfidenceBadge.tsx
│       │   ├── documents/
│       │   │   ├── DocumentTable.tsx
│       │   │   └── UploadDropzone.tsx
│       │   └── layout/
│       │       ├── AppShell.tsx
│       │       └── Sidebar.tsx
│       │
│       ├── hooks/
│       │   ├── useChat.ts
│       │   └── useDocuments.ts
│       │
│       ├── types/
│       │   ├── auth.ts
│       │   ├── chat.ts
│       │   └── documents.ts
│       │
│       └── utils/
│           └── tokenStorage.ts
│
├── scripts/
│   ├── seed_users.py                  # Dev admin/hr/finance/employee
│   ├── seed_documents.py              # Load fixtures into DB + storage
│   └── reindex_all.py                 # CLI reindex
│
└── results/                           # Test output (gitignored)
```

---

## 2. Major Folder Explanations

### Root

| Path | Purpose |
|------|---------|
| `README.md` | Product overview, setup, and run instructions |
| `docker-compose.yml` | Local dev stack: PostgreSQL, backend, frontend |
| `.env.example` | Template for secrets and configuration |
| `docs/` | Architecture, API, RBAC, and decision records |
| `scripts/` | One-off CLI utilities (seed, reindex) |
| `results/` | Generated test output |

### `backend/`

Python monolith. All server-side logic lives here.

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry point, startup/shutdown, CORS |
| `app/config.py` | Environment-driven settings |
| `app/dependencies.py` | Dependency injection for routes |
| `app/api/` | HTTP routes only — no business logic |
| `app/schemas/` | Pydantic models for API contracts |
| `app/services/` | Use-case orchestration and transactions |
| `app/rag/` | RAG engine: routing, retrieval, answers, index |
| `app/ingestion/` | Upload → parse → chunk → persist pipeline |
| `app/auth/` | JWT, passwords, role helpers |
| `app/rbac/` | Document and category authorization |
| `app/audit/` | Structured audit event logging |
| `app/db/` | SQLAlchemy models, sessions, repositories |
| `app/storage/` | File storage abstraction (local disk in MVP) |
| `app/integrations/` | Future Slack, Teams, SharePoint connectors |
| `app/core/` | Shared exceptions, logging, tenancy placeholder |
| `backend/storage/` | Runtime files and FAISS indexes (gitignored) |
| `backend/tests/` | Unit, integration, and RAG test suites |

### `frontend/`

React SPA. Talks only to the FastAPI backend via JWT-authenticated HTTP.

| Path | Purpose |
|------|---------|
| `src/api/` | HTTP client and endpoint wrappers |
| `src/auth/` | Login state, token storage, route guards |
| `src/pages/` | Top-level views (login, chat, documents, audit) |
| `src/components/` | Reusable UI (chat, documents, layout) |
| `src/hooks/` | Data-fetching and state hooks |
| `src/types/` | TypeScript interfaces matching API schemas |

---

## 3. Backend Module Responsibilities

### API layer (`app/api/v1/`)

Thin controllers: validate input → call service → return schema. No business logic.

| Module | Endpoints |
|--------|-----------|
| `auth.py` | Login, refresh, current user |
| `documents.py` | Upload, list, delete, reindex |
| `chat.py` | Conversations and messages |
| `audit.py` | Audit log queries (admin) |
| `health.py` | Liveness and readiness |

### Service layer (`app/services/`)

| Service | Responsibility |
|---------|----------------|
| `auth_service` | Login, token refresh, user lookup |
| `document_service` | Upload, delete, list, trigger reindex |
| `chat_service` | Conversations, persist messages, call RAG |
| `rag_service` | Pass user role and allowed categories to engine |
| `audit_service` | Record and query audit events |

### RAG engine (`app/rag/`)

| Module | Responsibility |
|--------|----------------|
| `engine.py` | Orchestrator (`EnterpriseRAG` from prototype) |
| `index_manager.py` | Build, persist, reload FAISS index |
| `retriever.py` | Embeddings and vector search |
| `router.py` | Keyword-based query routing |
| `answer_generator.py` | Natural-language answer synthesis |
| `rbac.py` | Category-level access rules |
| `types.py` | Citation, QueryResponse, RetrievalResult |

### Ingestion pipeline (`app/ingestion/`)

```
Upload → validate → store file → parse → categorize → chunk → save to DB → update FAISS index
```

| Module | Responsibility |
|--------|----------------|
| `loader.py` | Parse PDF, TXT, CSV, JSON |
| `chunker.py` | Split text with overlap |
| `categorizer.py` | Map file/metadata to category |
| `pipeline.py` | End-to-end ingest orchestration |
| `supported_types.py` | Allowed MIME types and extensions |

### Auth module (`app/auth/`)

| Module | Responsibility |
|--------|----------------|
| `jwt.py` | Create and verify access/refresh tokens |
| `password.py` | bcrypt hash and verify |
| `roles.py` | `admin`, `hr`, `finance`, `employee` |
| `security.py` | `get_current_user`, `require_role` dependencies |

### RBAC module (`app/rbac/`)

| Module | Responsibility |
|--------|----------------|
| `permissions.py` | Role → category/document rules |
| `policy.py` | `can_access(user, resource)` |
| `document_acl.py` | Per-document permissions in Postgres |

### Audit module (`app/audit/`)

| Module | Responsibility |
|--------|----------------|
| `events.py` | Event type constants |
| `logger.py` | `write_audit_event()` |
| `middleware.py` | Optional request-level logging |

---

## 4. Database Module Layout

```
backend/app/db/
├── session.py              # Engine, SessionLocal, get_db()
├── base.py                 # Declarative Base
├── models/
│   ├── user.py             # email, password_hash, role, is_active
│   ├── document.py         # filename, category, storage_path, status
│   ├── document_chunk.py   # chunk text, embedding_id
│   ├── document_permission.py  # role → document ACL
│   ├── conversation.py     # user chat sessions
│   ├── message.py          # query/answer with sources JSON
│   └── audit_log.py        # user actions, access, denials
└── repositories/           # CRUD and query helpers
```

### MVP tables

| Table | Purpose |
|-------|---------|
| `users` | Authentication and role |
| `documents` | Uploaded file metadata |
| `document_chunks` | Chunk text linked to vector index |
| `document_permissions` | Role-based document access |
| `conversations` | Chat sessions |
| `messages` | Query/answer history with citations |
| `audit_logs` | All auditable actions |

FAISS vectors stay on disk in `backend/storage/indexes/` for MVP. Postgres stores chunk metadata and `embedding_id` mapping.

---

## 5. API Route Layout

Base path: `/api/v1`

```
POST   /auth/login
POST   /auth/refresh
GET    /auth/me

GET    /documents
POST   /documents
GET    /documents/{id}
DELETE /documents/{id}
POST   /documents/{id}/reindex
POST   /documents/reindex-all          # admin

GET    /conversations
POST   /conversations
GET    /conversations/{id}
DELETE /conversations/{id}
POST   /conversations/{id}/messages

GET    /audit/logs                     # admin
GET    /audit/queries                  # admin

GET    /health
GET    /ready
```

All routes except `/auth/login`, `/health`, and `/ready` require JWT.

---

## 6. Request Flow

### Chat query

```
React ChatPage
    → POST /api/v1/conversations/{id}/messages
    → chat_service.send_message()
    → rag_service.query(user, query)
        → rbac/policy.py          (allowed categories + documents)
        → rag/router.py           (route to category)
        → rag/rbac.py             (deny if category blocked)
        → rag/retriever.py        (FAISS search)
        → rag/answer_generator.py (synthesize answer)
        → rag/engine.py           (citations + confidence)
    → db: save assistant message
    → audit: QUERY_EXECUTED or ACCESS_DENIED
    → JSON response to frontend
```

### Document upload

```
React DocumentsPage
    → POST /api/v1/documents
    → document_service.upload()
        → storage/local.py        (save raw file)
        → db: insert document     (status = pending)
        → ingestion/pipeline.py   (parse, chunk, persist)
        → rag/index_manager.py    (embed, update FAISS)
        → db: status = indexed
    → audit: DOCUMENT_UPLOADED, DOCUMENT_INDEXED
```

---

## 7. Prototype Migration Map

Current prototype files at repository root → target locations:

| Current file | Target location | Notes |
|--------------|-----------------|-------|
| `app.py` | `backend/app/rag/engine.py` | `EnterpriseRAG` orchestrator |
| `app.py` (`Citation`, `QueryResponse`) | `backend/app/rag/types.py` | Shared types |
| `loader.py` | `backend/app/ingestion/loader.py` | Add DB-aware ingestion |
| `loader.py` (`CATEGORY_MAP`) | `backend/app/ingestion/categorizer.py` | Also read from DB metadata |
| `loader.py` (chunking) | `backend/app/ingestion/chunker.py` | Extract chunk size/overlap |
| `retriever.py` | `backend/app/rag/retriever.py` | Index from `storage/indexes/` |
| `router.py` | `backend/app/rag/router.py` | Unchanged logic initially |
| `rbac.py` | `backend/app/rag/rbac.py` + `backend/app/rbac/policy.py` | Split category vs document ACL |
| `answer_generator.py` | `backend/app/rag/answer_generator.py` | Unchanged logic initially |
| `data/` | `backend/tests/fixtures/sample_docs/` | Test seed data |
| `data/` (runtime) | `backend/storage/documents/` | Production uploads |
| `test_pipeline.py` | `backend/tests/rag/test_pipeline.py` | Update imports |
| `realistic_enterprise_test.py` | `backend/tests/rag/realistic_enterprise_test.py` | Update imports |
| `results/` | `results/` (repo root) | Test output |
| `architecture.md` | `docs/architecture.md` | Expand for product |
| `requirements.txt` | `backend/requirements.txt` | Add FastAPI, SQLAlchemy, Alembic, JWT |

### New modules (no prototype equivalent)

- `app/api/`, `app/schemas/`, `app/services/`
- `app/db/`, `app/auth/`, `app/audit/`
- `app/rag/index_manager.py`
- `app/ingestion/pipeline.py`
- Entire `frontend/`

---

## 8. Future Expansion Points

### Slack

```
backend/app/integrations/slack/
├── bot.py              # Slack Bolt app
├── handlers.py         # Events → chat_service.send_message()
└── config.py
```

### Microsoft Teams

```
backend/app/integrations/teams/
├── bot.py              # Bot Framework adapter
└── handlers.py
```

### SharePoint

```
backend/app/integrations/sharepoint/
├── connector.py        # Implements integrations/base.py
├── sync_job.py         # Periodic pull → ingestion/pipeline.py
└── oauth.py            # Microsoft Graph auth
```

### Multi-tenancy (SaaS)

| Concern | MVP | SaaS evolution |
|---------|-----|----------------|
| Tenant isolation | Single fixed `tenant_id` | `tenant_id` on all rows |
| Vector index | One FAISS index | Per-tenant index or metadata filter |
| Auth | JWT with role | SSO (OIDC), tenant-scoped users |
| Storage | Local disk | S3 with per-tenant prefixes |
| Integrations | Stubs | Per-tenant Slack/Teams/SharePoint config |

Add `tenant_id` to: `users`, `documents`, `conversations`, `audit_logs`, `document_permissions`. Filter all repository queries by `tenant_id`.

---

## 9. Recommended Development Order

| Phase | Focus | Outcome |
|-------|-------|---------|
| 1. Foundation | Repo structure, Docker, Postgres, Alembic, health routes | Backend boots, DB migrates |
| 2. Auth | User model, seed script, JWT login | Login via API |
| 3. Migrate RAG | Move prototype to `rag/` + `ingestion/`, fix tests | RAG runs in new package |
| 4. Documents | Upload/list/delete API, ingestion, index_manager | Docs in DB + FAISS |
| 5. RBAC | Document permissions wired into RAG + API | Role-based access |
| 6. Chat API | Conversations, messages, citations, confidence | Backend MVP complete |
| 7. Audit | Audit model + logging on key actions | Admin audit endpoint |
| 8. React shell | Login, JWT client, protected routes | Frontend auth |
| 9. Chat UI | Chat window, citations, confidence | Knowledge Assistant UX |
| 10. Documents UI | Upload, list, delete, reindex | Document management UX |
| 11. Admin UI | Audit log page | Compliance visibility |
| 12. Hardening | Integration tests, error handling, docs | Production-ready MVP |

Within each phase: **DB model → repository → service → API route → test → frontend (if applicable)**.

---

## 10. Design Principles

1. **Monolith, layered** — API → Service → Domain (RAG/Ingestion) → DB/Storage
2. **Prototype RAG isolated** in `backend/app/rag/` — minimal changes at first
3. **RBAC split** — category rules (RAG) + document ACL (Postgres)
4. **Integrations are adapters** — never duplicate RAG logic
5. **`tenant_id` everywhere** — unused in MVP, ready for SaaS
6. **FAISS on disk for MVP** — swap via `index_manager.py` without touching API layers
7. **No microservices, no agents** — simple monolith scalable to SaaS later
