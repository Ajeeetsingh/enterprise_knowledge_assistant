"""Singleton manager for the shared sentence-transformers embedding model."""

from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger, log_with_fields
from app.rag.types import EMBEDDING_MODEL_NAME

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)


class EmbeddingModelManager:
    """Load and reuse a single ``SentenceTransformer`` instance process-wide.

    All ingestion, vector search, and legacy retrieval paths should obtain
    the model through this manager rather than constructing their own
    ``SentenceTransformer(...)``.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._load_lock = threading.Lock()
        self._load_duration_ms: float | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def load_duration_ms(self) -> float | None:
        return self._load_duration_ms

    def _configure_hub_environment(self) -> None:
        """Reduce Hugging Face hub chatter; respect offline mode when configured."""
        from app.config import get_settings

        settings = get_settings()
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
        if settings.embedding_local_only or os.environ.get(
            "EK_EMBEDDING_LOCAL_ONLY", ""
        ).lower() in ("1", "true", "yes"):
            os.environ["HF_HUB_OFFLINE"] = "1"

    def get_model(self) -> SentenceTransformer:
        """Return the shared model, loading it on first access."""
        if self._model is not None:
            return self._model

        with self._load_lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required. "
                    "Install it with: pip install sentence-transformers"
                ) from exc

            self._configure_hub_environment()
            local_only = os.environ.get("HF_HUB_OFFLINE", "") == "1"

            log_with_fields(
                logger,
                logging.INFO,
                "Loading shared embedding model",
                model=self._model_name,
                local_files_only=local_only,
            )
            started = time.perf_counter()
            self._model = SentenceTransformer(
                self._model_name,
                local_files_only=local_only,
            )
            self._load_duration_ms = round((time.perf_counter() - started) * 1000, 2)
            dimension = getattr(self._model, "get_embedding_dimension", None)
            if callable(dimension):
                dim = dimension()
            else:
                dim = self._model.get_sentence_embedding_dimension()
            log_with_fields(
                logger,
                logging.INFO,
                "Shared embedding model loaded",
                model=self._model_name,
                dimension=dim,
                load_duration_ms=self._load_duration_ms,
            )
            return self._model

    def preload(self) -> SentenceTransformer:
        """Eagerly load the model during application startup."""
        return self.get_model()

    def encode(self, texts: list[str], **kwargs: Any):
        """Encode texts using the shared model."""
        if not texts:
            return []
        defaults = {"convert_to_numpy": True, "show_progress_bar": False}
        defaults.update(kwargs)
        return self.get_model().encode(texts, **defaults)

    @property
    def dimension(self) -> int:
        model = self.get_model()
        getter = getattr(model, "get_embedding_dimension", None)
        if callable(getter):
            return int(getter())
        return int(model.get_sentence_embedding_dimension())


@lru_cache
def get_embedding_manager() -> EmbeddingModelManager:
    """Return the process-wide embedding model manager."""
    return EmbeddingModelManager()
