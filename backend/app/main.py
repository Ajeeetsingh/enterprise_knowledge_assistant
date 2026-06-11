"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.logging import get_logger, log_with_fields, setup_logging
from app.db.session import check_database_connection, engine

logger = get_logger(__name__)


def _ensure_storage_directories() -> None:
    """Create local filesystem storage directories if missing."""
    settings = get_settings()
    settings.documents_path.mkdir(parents=True, exist_ok=True)
    settings.indexes_path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    setup_logging()

    log_with_fields(
        logger,
        logging.INFO,
        "Application starting",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        tenant_id=settings.tenant_id,
    )

    _ensure_storage_directories()

    db_ok = check_database_connection()
    log_with_fields(
        logger,
        logging.INFO,
        "Database connectivity check",
        database="connected" if db_ok else "unavailable",
    )

    yield

    log_with_fields(logger, logging.INFO, "Application shutting down")
    engine.dispose()
    log_with_fields(logger, logging.INFO, "Database engine disposed")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoints at root (container/orchestrator probes)
    application.include_router(api_router)

    # API v1 routes (future modules mount here)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
