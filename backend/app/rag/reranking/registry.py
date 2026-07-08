"""Registry-driven cross-encoder reranker configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "models.json"


class RerankerRegistryError(ValueError):
    """Raised when the reranker registry is invalid or a model is unknown."""


@dataclass(frozen=True)
class RerankerModelSpec:
    """Declarative cross-encoder reranker configuration."""

    id: str
    label: str
    model_name: str
    is_default: bool = False
    max_sequence_length: int = 512


def _parse_spec(raw: dict[str, Any]) -> RerankerModelSpec:
    required = ("id", "label", "model_name")
    missing = [field for field in required if field not in raw]
    if missing:
        raise RerankerRegistryError(
            f"Model entry missing required fields: {', '.join(missing)}"
        )
    return RerankerModelSpec(
        id=str(raw["id"]),
        label=str(raw["label"]),
        model_name=str(raw["model_name"]),
        is_default=bool(raw.get("is_default", False)),
        max_sequence_length=int(raw.get("max_sequence_length", 512)),
    )


def load_reranker_registry(
    registry_path: str | Path | None = None,
) -> list[RerankerModelSpec]:
    path = Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH
    if not path.exists():
        raise RerankerRegistryError(f"Reranker registry not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    models_raw = payload.get("models", [])
    if not isinstance(models_raw, list) or not models_raw:
        raise RerankerRegistryError("Registry must contain a non-empty 'models' list.")

    specs = [_parse_spec(item) for item in models_raw]
    if len({spec.id for spec in specs}) != len(specs):
        raise RerankerRegistryError("Duplicate reranker model ids found in registry.")

    defaults = [spec for spec in specs if spec.is_default]
    if len(defaults) != 1:
        raise RerankerRegistryError(
            "Registry must define exactly one default model (is_default=true)."
        )
    return specs


@lru_cache
def _registry_index(registry_path: str) -> dict[str, RerankerModelSpec]:
    return {spec.id: spec for spec in load_reranker_registry(registry_path)}


def get_model_spec(
    model_id: str,
    *,
    registry_path: str | Path | None = None,
) -> RerankerModelSpec:
    path = str(Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH)
    spec = _registry_index(path).get(model_id)
    if spec is None:
        raise RerankerRegistryError(f"Unknown reranker model id: {model_id}")
    return spec


def get_default_spec(
    *,
    registry_path: str | Path | None = None,
) -> RerankerModelSpec:
    for spec in load_reranker_registry(registry_path):
        if spec.is_default:
            return spec
    raise RerankerRegistryError("No default reranker model configured in registry.")
