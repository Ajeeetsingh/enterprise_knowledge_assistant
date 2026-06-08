"""Single-tenant MVP tenancy placeholder."""

from app.config import get_settings


def get_tenant_id() -> str:
    """Return the active tenant identifier (fixed for MVP)."""
    return get_settings().tenant_id
