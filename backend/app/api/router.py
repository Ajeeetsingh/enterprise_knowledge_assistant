"""Aggregates all API route modules."""

from fastapi import APIRouter

from app.api.v1 import analytics_ai, analytics_errors, analytics_knowledge, analytics_monitoring, analytics_users, audit, auth, chat, conversations, documents, health, monitoring, reports, roles, user_roles, users, workspace

# Liveness/readiness probes for Docker and orchestrators (no /api/v1 prefix).
health_router = APIRouter()
health_router.include_router(health.router, tags=["health"])

# Versioned application API — auth, users, roles, etc.
api_v1_router = APIRouter()
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"],
)
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(user_roles.router, prefix="/users", tags=["user-roles"])
api_v1_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_v1_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_v1_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["monitoring"],
)
api_v1_router.include_router(
    analytics_users.router,
    prefix="/admin/analytics/users",
    tags=["analytics"],
)
api_v1_router.include_router(
    analytics_ai.router,
    prefix="/admin/analytics/ai",
    tags=["analytics"],
)
api_v1_router.include_router(
    analytics_knowledge.router,
    prefix="/admin/analytics/knowledge",
    tags=["analytics"],
)
api_v1_router.include_router(
    analytics_monitoring.router,
    prefix="/admin/analytics/monitoring",
    tags=["analytics"],
)
api_v1_router.include_router(
    analytics_errors.router,
    prefix="/admin/analytics/errors",
    tags=["analytics"],
)
api_v1_router.include_router(
    reports.router,
    prefix="/admin/reports",
    tags=["reports"],
)

# Alias kept for any existing imports.
api_router = api_v1_router
