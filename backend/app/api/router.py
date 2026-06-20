"""Aggregates all API route modules."""

from fastapi import APIRouter

from app.api.v1 import auth, chat, documents, health, roles, user_roles, users

# Liveness/readiness probes for Docker and orchestrators (no /api/v1 prefix).
health_router = APIRouter()
health_router.include_router(health.router, tags=["health"])

# Versioned application API — auth, users, roles, etc.
api_v1_router = APIRouter()
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(user_roles.router, prefix="/users", tags=["user-roles"])
api_v1_router.include_router(roles.router, prefix="/roles", tags=["roles"])

# Alias kept for any existing imports.
api_router = api_v1_router
