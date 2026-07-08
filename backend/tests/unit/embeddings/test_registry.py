"""Unit tests for the embedding model registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.embeddings.registry import (
    EmbeddingRegistryError,
    get_baseline_spec,
    get_model_spec,
    load_embedding_registry,
    resolve_model_specs,
)
from app.rag.types import EMBEDDING_MODEL_NAME


def test_load_embedding_registry_contains_baseline() -> None:
    registry = load_embedding_registry()
    assert len(registry) >= 6
    baseline = get_baseline_spec()
    assert baseline.model_name == EMBEDDING_MODEL_NAME
    assert baseline.is_baseline is True


def test_get_model_spec_returns_requested_model() -> None:
    spec = get_model_spec("bge-small-en-v1.5")
    assert spec.model_name == "BAAI/bge-small-en-v1.5"


def test_resolve_model_specs_filters_ids() -> None:
    specs = resolve_model_specs(["minilm-l6-v2", "e5-base-v2"])
    assert [spec.id for spec in specs] == ["minilm-l6-v2", "e5-base-v2"]


def test_registry_rejects_unknown_model(tmp_path: Path) -> None:
    payload = {
        "models": [
            {
                "id": "only",
                "label": "Only",
                "model_name": EMBEDDING_MODEL_NAME,
                "is_baseline": True,
            }
        ]
    }
    path = tmp_path / "models.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EmbeddingRegistryError, match="Unknown embedding model id"):
        get_model_spec("missing", registry_path=path)
