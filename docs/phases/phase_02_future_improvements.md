# Phase 02 — Future Improvements

**Project:** Enterprise Knowledge Assistant  
**Scope:** Authentication & authorization subsystem (Phases 2.1–2.7)  
**Status:** Recommendations only — not implemented

This document captures intentional deferrals and production hardening opportunities identified during the Phase 2.8 review. Items here are **not blockers** for Phase 3 (RAG integration).

---

## Security Hardening

### Rate limiting

Add rate limiting on `POST /auth/login` and `POST /auth/refresh` to mitigate brute-force and token-grinding attacks. Consider per-IP and per-email buckets.

### Refresh token persistence

Store refresh tokens (or hashed token IDs) in PostgreSQL with `user_id`, `issued_at`, `expires_at`, and `revoked_at`. Enables true logout and session management.

### Token revocation / blacklist

Maintain a denylist of revoked refresh tokens (and optionally access token JTIs) checked during `verify_token` or refresh. Required for immediate access revocation after logout or admin deactivation.

### Password reset

Add secure forgot-password / reset-password flow with time-limited single-use tokens sent via email.

### Email verification

Require verified email before full account activation; store `email_verified_at` on the user record.

### Multi-factor authentication (MFA)

Support TOTP or WebAuthn for admin and high-privilege accounts.

### JWT secret rotation

Document and automate rotation of `JWT_SECRET` with overlapping validation windows to avoid forced global logout during rotation.

### Production secret enforcement

Fail fast at startup when `JWT_SECRET` is the default value and `APP_ENV=production`.

---

## Operational & Compliance

### Audit logging

Record authentication events: login success/failure, refresh, logout, user CRUD, role assignment/removal, and authorization denials. Feeds Phase 7 audit module.

### Structured auth metrics

Emit counters for login failures, token validation errors, and 403 rates for monitoring dashboards.

---

## API & UX

### Password change endpoint

Authenticated users should change password via `POST /auth/change-password` with current-password verification.

### Consistent API surface

Phase 1 registers routes at both `/` and `/api/v1`. Consider deprecating unprefixed duplicates in OpenAPI for external clients.

### Role assignment and JWT freshness

Document (or add) optional token invalidation when roles change, or require re-login after role updates for immediate effect.

---

## Data & Architecture

### Shared user lookup helper

`auth_service` and `user_service` both contain similar user-by-id/email queries. A thin `user_repository` module could deduplicate without changing public APIs.

### Unified service exceptions

`AuthServiceError`, `UserServiceError`, and `RoleServiceError` follow the same pattern; a shared `AppServiceError` base in `app/core/exceptions.py` would reduce repetition.

### Seed admin user script

Add `scripts/seed_admin_user.py` for local/dev bootstrap (complements existing `seed_roles.py`).

---

## Testing & Performance

### bcrypt test performance

Integration tests hash passwords per fixture (~30+ minutes for full auth suite on Windows). Options:

- Use `bcrypt` with reduced rounds in test settings only
- Pre-compute static password hashes in fixtures
- Mark slow auth integration tests and run separately in CI

### Auth test markers

Add pytest markers: `auth`, `auth_slow`, `auth_unit` for selective CI pipelines.

### End-to-end auth flow test

Single test covering login → `/me` → protected admin route → refresh → `/me` with new token.

---

## Dependencies

### Passlib / bcrypt compatibility

`bcrypt` is pinned `<5.0.0` for Passlib 1.7.4 compatibility. Plan migration to `bcrypt` 5.x or native `bcrypt` hashing when Passlib maintenance status is resolved.

### `email-validator`

Required for `EmailStr` schemas; ensure it remains in `requirements.txt` (added in Phase 2.4A).

---

## Phase 3 Readiness

The authentication subsystem is **production-ready for Phase 3** with the understanding that items above are follow-up hardening, not prerequisites for RAG service integration.
