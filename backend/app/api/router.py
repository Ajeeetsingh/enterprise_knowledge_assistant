"""Aggregates all API route modules."""

from fastapi import APIRouter

from app.api.v1 import auth, health, roles, user_roles, users

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(user_roles.router, prefix="/users", tags=["user-roles"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
