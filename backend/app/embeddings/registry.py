"""Configuration-driven embedding model registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "models.json"


class EmbeddingRegistryError(ValueError):
    """Raised when the embedding registry is invalid or a model is unknown."""


@dataclass(frozen=True)
class EmbeddingModelSpec:
    """Declarative embedding model configuration."""

    id: str
    label: str
    model_name: str
    is_baseline: bool = False
    provider: str = "sentence_transformers"


def _parse_spec(raw: dict[str, Any]) -> EmbeddingModelSpec:
    required = ("id", "label", "model_name")
    missing = [field for field in required if field not in raw]
    if missing:
        raise EmbeddingRegistryError(
            f"Model entry missing required fields: {', '.join(missing)}"
        )
    return EmbeddingModelSpec(
        id=str(raw["id"]),
        label=str(raw["label"]),
        model_name=str(raw["model_name"]),
        is_baseline=bool(raw.get("is_baseline", False)),
        provider=str(raw.get("provider", "sentence_transformers")),
    )


def load_embedding_registry(
    registry_path: str | Path | None = None,
) -> list[EmbeddingModelSpec]:
    """Load all embedding model specifications from the registry file."""
    path = Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH
    if not path.exists():
        raise EmbeddingRegistryError(f"Embedding registry not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    models_raw = payload.get("models", [])
    if not isinstance(models_raw, list) or not models_raw:
        raise EmbeddingRegistryError("Registry must contain a non-empty 'models' list.")

    specs = [_parse_spec(item) for item in models_raw]
    seen_ids = {spec.id for spec in specs}
    if len(seen_ids) != len(specs):
        raise EmbeddingRegistryError("Duplicate model ids found in embedding registry.")

    baselines = [spec for spec in specs if spec.is_baseline]
    if len(baselines) != 1:
        raise EmbeddingRegistryError(
            "Registry must define exactly one baseline model (is_baseline=true)."
        )
    return specs


@lru_cache
def _registry_index(
    registry_path: str,
) -> dict[str, EmbeddingModelSpec]:
    return {spec.id: spec for spec in load_embedding_registry(registry_path)}


def get_model_spec(
    model_id: str,
    *,
    registry_path: str | Path | None = None,
) -> EmbeddingModelSpec:
    """Return a single model specification by id."""
    path = str(Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH)
    index = _registry_index(path)
    spec = index.get(model_id)
    if spec is None:
        raise EmbeddingRegistryError(f"Unknown embedding model id: {model_id}")
    return spec


def get_baseline_spec(
    *,
    registry_path: str | Path | None = None,
) -> EmbeddingModelSpec:
    """Return the production baseline embedding model specification."""
    for spec in load_embedding_registry(registry_path):
        if spec.is_baseline:
            return spec
    raise EmbeddingRegistryError("No baseline model configured in registry.")


def resolve_model_specs(
    model_ids: list[str] | None = None,
    *,
    registry_path: str | Path | None = None,
) -> list[EmbeddingModelSpec]:
    """Resolve model specs for evaluation.

    When ``model_ids`` is omitted, all registry models are returned in file order.
    """
    specs = load_embedding_registry(registry_path)
    if not model_ids:
        return specs

    resolved: list[EmbeddingModelSpec] = []
    for model_id in model_ids:
        resolved.append(get_model_spec(model_id, registry_path=registry_path))
    return resolved
