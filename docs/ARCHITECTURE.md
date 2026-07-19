# Architecture

Enterprise Knowledge Assistant is a layered monolithic application: a React SPA talks to a FastAPI API that owns authentication, document ingestion, RAG retrieval, and administration. PostgreSQL stores application data; uploaded files and vector/BM25 indexes live on local filesystem storage (or Docker volumes).

## High-level view

```
React (Vite)  ──HTTPS──►  FastAPI (/api/v1, /health)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           Auth/RBAC    Document Service   Chat / RAG
              │               │               │
              │               ▼               ▼
              │        Ingestion pipeline   Hybrid retrieval
              │               │               │
              └──────► PostgreSQL ◄───────────┘
                              │
                    Local storage/
                      documents/   uploaded files
                      indexes/     FAISS + BM25 state
```

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL 16 |
| Embeddings | Sentence Transformers (configurable) |
| Sparse retrieval | BM25 |
| Dense retrieval | FAISS |
| Reranking | Cross-encoder (ms-marco MiniLM by default) |
| LLM | Provider-agnostic (Groq / OpenAI / Gemini / Ollama / none) |
| Packaging | Docker Compose |

## Ingestion pipeline

```
Upload → validate → store file → extract text
  → normalize → structure extraction → semantic chunking
  → embeddings → FAISS + BM25 index update → searchable metadata
```

Owned by `DocumentService` → `IngestionPipeline` under `backend/app/ingestion/`.

Multi-file upload, content checksums, and tenant-scoped duplicate detection prevent re-ingesting identical files.

## Retrieval / answer pipeline

```
Question → query intelligence (expand / multi-query)
  → hybrid retrieve (dense FAISS + sparse BM25 + RRF)
  → metadata-aware rescoring
  → cross-encoder rerank
  → authorization filter (fail-closed)
  → LLM generation → answer + citations
```

Entry: `RagService` → `EnterpriseRAG` (`backend/app/rag/`).

Authorization filtering uses the authenticated user's roles and each document's ACL (visibility / allowed roles / owner). Retrieval fails closed: inaccessible chunks are never returned as evidence.

## Security model

- **Authentication:** JWT access + refresh tokens (`/auth/login`, `/auth/refresh`, `/auth/me`).
- **Public registration:** `/auth/register` always assigns **Employee** server-side; clients cannot submit roles.
- **RBAC:** System roles Admin, HR, Finance, Employee map to permissions in `backend/app/auth/role_permissions.py`.
- **Document ACL:** visibility + `allowed_roles` + owner checks in `DocumentAuthorizationService`.
- **Admin user management:** create-with-role (atomic), role change, enable/disable, last-admin lockout protection.
- **Uploads:** type/size validation, rate limiting on sensitive public endpoints.
- **Production JWT:** non-development `APP_ENV` rejects the placeholder `JWT_SECRET`.

Frontend permission helpers mirror backend maps for UX only. **Backend authorization is the security boundary.**

## Roles

| Role | Typical access |
|------|----------------|
| Admin | Full platform administration, user management, analytics |
| HR | HR-oriented documents + knowledge query (create/update where permitted) |
| Finance | Finance-oriented read + knowledge query |
| Employee | Default self-registered role; read + knowledge query within ACL |

Privileged roles are assigned only by admins (or seed scripts in development).

## Frontend surfaces

- Public landing + `/register` + `/login`
- Authenticated dashboard, chat, documents, profile
- Admin portal (`/admin/*`): users, documents, uploads, analytics, reports
- Dev-only routes (`auth-debug`, design-system, etc.) are compiled out of production builds via `import.meta.env.DEV`

## Persistence

| Data | Location |
|------|----------|
| Users, roles, conversations, documents metadata, audit | PostgreSQL |
| Uploaded binaries | `backend/storage/documents` |
| FAISS / BM25 indexes | `backend/storage/indexes` |

Index bootstrap on startup rebuilds searchable state from the database when needed (`bootstrap_search_index`). Demo users are **not** created on startup.
