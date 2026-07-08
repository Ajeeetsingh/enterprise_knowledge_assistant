"""Cross-encoder runtime and model loading."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from app.core.logging import get_logger, log_with_fields
from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.registry import RerankerModelSpec, get_model_spec

logger = get_logger(__name__)


def _resolve_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class CrossEncoderRuntime:
    """Lazy-loaded cross-encoder model with batch inference support."""

    def __init__(
        self,
        spec: RerankerModelSpec,
        *,
        settings: RerankingSettings,
    ) -> None:
        self._spec = spec
        self._settings = settings
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        self._load_duration_ms: float | None = None
        self._device = _resolve_device()

    @property
    def spec(self) -> RerankerModelSpec:
        return self._spec

    @property
    def model_name(self) -> str:
        return self._spec.model_name

    @property
    def device(self) -> str:
        return self._device

    @property
    def load_duration_ms(self) -> float | None:
        return self._load_duration_ms

    def _configure_hub_environment(self) -> None:
        from app.config import get_settings

        settings = get_settings()
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
        if settings.embedding_local_only or os.environ.get(
            "EK_EMBEDDING_LOCAL_ONLY", ""
        ).lower() in ("1", "true", "yes"):
            os.environ["HF_HUB_OFFLINE"] = "1"

    def get_model(self):
        if self._model is not None:
            return self._model

        with self._load_lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for cross-encoder reranking."
                ) from exc

            self._configure_hub_environment()
            local_only = os.environ.get("HF_HUB_OFFLINE", "") == "1"
            max_length = min(
                self._settings.max_sequence_length,
                self._spec.max_sequence_length,
            )

            log_with_fields(
                logger,
                logging.INFO,
                "Loading cross-encoder reranker",
                model=self._spec.model_name,
                device=self._device,
                max_length=max_length,
                local_files_only=local_only,
            )
            started = time.perf_counter()
            self._model = CrossEncoder(
                self._spec.model_name,
                max_length=max_length,
                device=self._device,
            )
            self._load_duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_with_fields(
                logger,
                logging.INFO,
                "Cross-encoder reranker loaded",
                model=self._spec.model_name,
                device=self._device,
                load_duration_ms=self._load_duration_ms,
            )
            return self._model

    def preload(self) -> None:
        self.get_model()


def create_reranker_runtime(
    settings: RerankingSettings | None = None,
) -> CrossEncoderRuntime:
    """Create a runtime for the configured reranker model."""
    resolved = settings or RerankingSettings.from_settings()
    spec = get_model_spec(resolved.rerank_model_id, registry_path=resolved.registry_path)
    return CrossEncoderRuntime(spec, settings=resolved)
