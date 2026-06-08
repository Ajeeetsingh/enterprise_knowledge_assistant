"""FastAPI dependency injection."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db as _get_db

# Re-export database session dependency
get_db = _get_db


def get_settings_dep() -> Settings:
    """Return application settings for route injection."""
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    """Alias for get_db — explicit session dependency."""
    yield from _get_db()
