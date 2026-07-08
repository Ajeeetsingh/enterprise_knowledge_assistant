"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router, health_router
from app.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger, log_with_fields, setup_logging
from app.db.session import SessionLocal, check_database_connection, engine
from app.embeddings.manager import get_embedding_manager
from app.services.document_service import get_document_service
from app.services.index_bootstrap_service import bootstrap_search_index
from app.services.rag_service import get_rag_service

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

    embedding_manager = get_embedding_manager()
    try:
        embedding_manager.preload()
        log_with_fields(
            logger,
            logging.INFO,
            "Embedding model preloaded",
            model=embedding_manager.model_name,
            load_duration_ms=embedding_manager.load_duration_ms,
        )
    except Exception as exc:
        log_with_fields(
            logger,
            logging.ERROR,
            "Embedding model preload failed",
            reason=type(exc).__name__,
        )

    if db_ok:
        try:
            with SessionLocal() as session:
                bootstrap_search_index(session, get_document_service())
            get_rag_service().initialize()
        except Exception as exc:
            log_with_fields(
                logger,
                logging.ERROR,
                "Knowledge index bootstrap failed",
                reason=type(exc).__name__,
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

    register_exception_handlers(application)

    # Health probes at root for Docker / orchestrators
    application.include_router(health_router)

    # All business API routes under /api/v1
    application.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
