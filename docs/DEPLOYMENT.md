# Deployment

Production-oriented deployment for a single-organisation portfolio or demo host.

Product and architecture context: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) · [ARCHITECTURE.md](ARCHITECTURE.md).  
Local development setup: [DEVELOPMENT.md](DEVELOPMENT.md).

## What this guide covers

- Environment configuration
- Database migrations and bootstrap
- Docker Compose production file
- Persistence
- Health checks
- Deployment checklist

This is **not** a multi-region SaaS / Kubernetes guide.

## Architecture of a typical deploy

1. **PostgreSQL** - private network only  
2. **Backend** (FastAPI / Uvicorn) - public HTTPS reverse-proxy in front  
3. **Frontend** - static build hosted separately (CDN, object storage, or nginx), with `VITE_API_BASE_URL` baked in at build time  

## Environment variables

Copy `.env.example` → `.env` on the server. Critical production settings:

| Variable | Requirement |
|----------|-------------|
| `APP_ENV` | Must be `production` (or `staging`) |
| `DEBUG` | `false` |
| `JWT_SECRET` | Strong random secret — **startup fails** if still `change-me-in-production` when `APP_ENV != development` |
| `DATABASE_URL` | Strong credentials; host reachable only inside the private network |
| `CORS_ORIGINS` | Exact frontend origin(s), JSON list |
| `GROQ_API_KEY` (or other provider) | Required for live LLM answers |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Required by `docker-compose.prod.yml` |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Frontend build:

```bash
cd frontend
# Point at the public API URL (no trailing slash)
echo "VITE_API_BASE_URL=https://api.example.com/api/v1" > .env.production
npm ci
npm run build
# Deploy the contents of frontend/dist/
```

## Database and bootstrap

```bash
# Inside the backend container or a one-shot job with DATABASE_URL set:
alembic upgrade head
python /path/to/scripts/seed_database.py --roles
```

### First administrator

**Do not** run `--demo` in production.

Recommended approaches:

1. **Local-style admin seed once**, then change the password immediately via a secure channel / DB update / dedicated password-reset flow you control:
   ```bash
   python scripts/seed_database.py --admin
   ```
   Default seed email is documented in `scripts/seeding/admin.py` for local use only. Treat it as a bootstrap secret and rotate it before exposing the site.

2. **Register** as Employee via `/register`, then promote that user to Admin using an authenticated admin session (requires an existing admin) or a controlled one-time maintenance script.

### Never auto-seed

Application startup (`backend/app/main.py`) bootstraps **search indexes** only. It does **not** create demo users, Quiet Employee, or known passwords.

## Docker

### Development

```bash
docker compose up postgres -d
# run backend/frontend on the host as in DEVELOPMENT.md
```

`docker-compose.yml` publishes Postgres and sets `APP_ENV=development` — **not** for public deploy.

### Production-like

```bash
# .env must define POSTGRES_USER, POSTGRES_PASSWORD, JWT_SECRET, APP_ENV=production, etc.
docker compose -f docker-compose.prod.yml up -d --build
```

Properties of `docker-compose.prod.yml`:

- Postgres **not** published to the host
- `APP_ENV=production`
- Restart policies
- Health checks
- Named volumes for Postgres data and `backend/storage` (uploads + indexes)
- Credentials via environment (no hardcoded production passwords)

Backend image runs as a non-root user (`appuser`).

Validate compose file:

```bash
docker compose -f docker-compose.prod.yml config
```

## Persistence across restarts

| Volume / path | Contents |
|---------------|----------|
| `postgres_data` | Users, roles, conversations, document metadata, audit |
| `backend_storage` → `/app/storage` | Uploaded documents + FAISS/BM25 indexes |

Losing `backend_storage` requires re-ingestion or index rebuild from searchable documents; losing Postgres loses application state.

## Health checks

- `GET /health` - liveness for Compose / load balancers  
- Optional readiness: confirm DB connectivity in your host’s monitoring  

## Deployment checklist

- [ ] `APP_ENV=production`, `DEBUG=false`
- [ ] Unique `JWT_SECRET`
- [ ] Strong DB password; Postgres not on the public internet
- [ ] `CORS_ORIGINS` limited to your frontend origin(s)
- [ ] LLM API key configured
- [ ] `alembic upgrade head` applied
- [ ] Roles seeded; first Admin created and password rotated
- [ ] `--demo` **not** run
- [ ] Frontend built with correct `VITE_API_BASE_URL`
- [ ] TLS terminated at reverse proxy
- [ ] Storage volumes backed up
- [ ] `/health` returns OK
- [ ] Public registration creates Employee only
- [ ] Duplicate upload returns safe “already exists” behaviour
- [ ] Restricted documents are not returned to unauthorized roles

## Known deployment limitations

- In-memory rate limiting (single backend process)
- Local FAISS files (not a managed vector DB)
- Single-organisation (`TENANT_ID`) model
- No enterprise SSO / IdP integration in this release
