# Architecture

Knowra is a layered monolithic application: a React SPA talks to a FastAPI API that owns authentication, document ingestion, RAG retrieval, and administration. PostgreSQL stores application data; uploaded files and vector/BM25 indexes live on local filesystem storage (or Docker volumes).

For a product-level explanation (features, roles, citation UX, limitations), see [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md). Production hosting steps live only in [DEPLOYMENT.md](DEPLOYMENT.md).

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
Question
  → QueryRouter (backend/app/query_router/)
       • UNSAFE → boundary response
       • PRODUCT_HELP → curated local answer
       • GENERAL_QUERY → configured LLM (capped history)
       • DOCUMENT_QUERY → continue below
  → authorized source filenames (fail-closed ACL)
  → query intelligence (expand / multi-query)
  → hybrid retrieve (dense FAISS + sparse BM25 + RRF)
      constrained to authorized sources
  → metadata-aware rescoring
  → cross-encoder rerank
  → LLM generation → answer + citations
```

Entry: `ConversationChatService` → `QueryRouter` → (DOCUMENT only) `RagService` → `EnterpriseRAG` (`backend/app/rag/`).

Zero accessible documents on a DOCUMENT route returns a curated message and skips retrieval. Contextual follow-ups may inherit the prior route when the current turn is ambiguous; they never change ACL. Citations are produced only for document-grounded RAG answers.

Authorized sources are computed from document ACL (visibility / allowed roles / owner) **before** retrieval and applied as a source filter. An empty authorized set retrieves nothing. Orphan index entries without a database row are denied.

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
- Authenticated dashboard (workspace summary), chat (suggested questions, citations), documents, profile
- Document viewer: cited page navigation + text-layer passage highlighting (progressive enhancement)
- Admin portal (`/admin/*`): users, documents, uploads, analytics, reports, monitoring
- Admin Collections UI is a local preview (not server-persisted); Admin home metrics use live monitoring resource APIs
- Dev-only routes (`auth-debug`, design-system, etc.) are compiled out of production builds via `import.meta.env.DEV`

## Persistence

| Data | Location |
|------|----------|
| Users, roles, conversations, documents metadata, audit | PostgreSQL |
| Uploaded binaries | `backend/storage/documents` |
| FAISS / BM25 indexes | `backend/storage/indexes` |

Index bootstrap on startup rebuilds searchable state from the database when needed (`bootstrap_search_index`). Demo users are **not** created on startup.
