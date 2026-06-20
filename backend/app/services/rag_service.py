"""RAG integration service — sole bridge between the backend and the RAG engine."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.core.exceptions import (
    RagInitializationError,
    RagRetrievalError,
    RagServiceError,
)
from app.core.logging import get_logger, log_with_fields

if TYPE_CHECKING:
    from app.rag.engine import EnterpriseRAG
    from app.rag.types import QueryResponse

logger = get_logger(__name__)


def _create_engine(data_dir: str) -> tuple["EnterpriseRAG", int]:
    """Construct and initialize the RAG engine (lazy import of heavy deps)."""
    from app.rag.engine import EnterpriseRAG

    engine = EnterpriseRAG(data_dir=data_dir)
    chunk_count = engine.initialize()
    return engine, chunk_count


class RagService:
    """Integration layer wrapping the production-tested EnterpriseRAG engine."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: EnterpriseRAG | None = None
        self._initialized = False
        self._chunk_count = 0
        self._init_lock = threading.Lock()

    @property
    def is_initialized(self) -> bool:
        """Return whether the underlying RAG engine has been initialized."""
        return self._initialized

    def initialize(self) -> int:
        """Load documents and build the RAG index.

        Idempotent — subsequent calls return without re-initializing.
        Returns the number of indexed document chunks.
        """
        if self._engine is not None and self._initialized:
            return self._chunk_count

        with self._init_lock:
            if self._engine is not None and self._initialized:
                return self._chunk_count

            data_dir = self._settings.documents_path
            log_with_fields(
                logger,
                logging.INFO,
                "RAG initialization started",
                data_dir=str(data_dir),
                indexes_path=str(self._settings.indexes_path),
            )

            try:
                engine, chunk_count = _create_engine(str(data_dir))
            except FileNotFoundError as exc:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason="data_directory_missing",
                    data_dir=str(data_dir),
                )
                raise RagInitializationError(
                    "Knowledge base data directory is not available."
                ) from exc
            except ValueError as exc:
                message = str(exc).lower()
                if "no document chunks" in message or "cannot build index" in message:
                    log_with_fields(
                        logger,
                        logging.ERROR,
                        "RAG initialization failed",
                        reason="empty_knowledge_base",
                        data_dir=str(data_dir),
                    )
                    raise RagInitializationError(
                        "Knowledge base contains no indexable documents."
                    ) from exc
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason="invalid_configuration",
                )
                raise RagInitializationError(
                    "Failed to initialize the knowledge retrieval engine."
                ) from exc
            except Exception as exc:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason=type(exc).__name__,
                )
                raise RagInitializationError(
                    "Failed to initialize the knowledge retrieval engine."
                ) from exc

            log_with_fields(
                logger,
                logging.INFO,
                "RAG initialization succeeded",
                chunk_count=chunk_count,
            )
            self._engine = engine
            self._initialized = True
            self._chunk_count = chunk_count
            return chunk_count

    def _ensure_initialized(self) -> EnterpriseRAG:
        """Return the initialized engine, initializing on first use."""
        if self._engine is None or not self._initialized:
            self.initialize()
        assert self._engine is not None
        return self._engine

    def answer_question(self, question: str, role: str) -> "QueryResponse":
        """Run a natural-language query through the RAG engine.

        Returns the native ``QueryResponse`` from the RAG engine.
        ``role`` is required by the engine for category-level RBAC.
        """
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Question must not be empty.")

        normalized_role = role.strip()
        if not normalized_role:
            raise ValueError("Role must not be empty.")

        engine = self._ensure_initialized()

        try:
            return engine.query(normalized_question, normalized_role)
        except RuntimeError as exc:
            message = str(exc).lower()
            if "index not built" in message or "not initialized" in message:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG retrieval failed",
                    reason="index_unavailable",
                )
                raise RagRetrievalError(
                    "Knowledge retrieval index is not available."
                ) from exc
            log_with_fields(
                logger,
                logging.ERROR,
                "RAG retrieval failed",
                reason="runtime_error",
            )
            raise RagRetrievalError("Knowledge retrieval failed.") from exc
        except RagServiceError:
            raise
        except Exception as exc:
            log_with_fields(
                logger,
                logging.ERROR,
                "RAG retrieval failed",
                reason=type(exc).__name__,
            )
            raise RagRetrievalError("Knowledge retrieval failed.") from exc


@lru_cache
def get_rag_service() -> RagService:
    """Return a cached RAG service instance."""
    return RagService(get_settings())
