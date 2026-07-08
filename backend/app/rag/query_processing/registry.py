"""Registry-driven query intelligence rules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules.json"


class QueryRulesRegistryError(ValueError):
    """Raised when query rules are invalid or missing."""


@dataclass(frozen=True)
class EntitySpec:
    """Canonical enterprise entity with aliases."""

    key: str
    canonical: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class StrategySpec:
    """Configurable retrieval strategy overrides."""

    name: str
    sparse_weight_multiplier: float = 1.0
    dense_weight_multiplier: float = 1.0
    metadata_bonus_multiplier: float = 1.0
    rerank_top_n: int = 20
    retrieval_depth_multiplier: float = 1.0


@dataclass(frozen=True)
class QueryRulesRegistry:
    """Loaded query intelligence rules."""

    acronyms: dict[str, tuple[str, ...]]
    synonyms: dict[str, tuple[str, ...]]
    entities: dict[str, EntitySpec]
    multi_query_variants: dict[str, tuple[str, ...]]
    strategies: dict[str, StrategySpec]


def _normalize_mapping(raw: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for key, values in raw.items():
        if isinstance(values, list):
            normalized[str(key).upper() if key.isupper() else str(key)] = tuple(str(v) for v in values)
        else:
            normalized[str(key)] = (str(values),)
    return normalized


def _parse_entities(raw: dict[str, Any]) -> dict[str, EntitySpec]:
    entities: dict[str, EntitySpec] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            raise QueryRulesRegistryError(f"Invalid entity entry for {key}")
        canonical = str(value.get("canonical", key))
        aliases_raw = value.get("aliases", [])
        aliases = tuple(str(item) for item in aliases_raw) if isinstance(aliases_raw, list) else ()
        entities[str(key)] = EntitySpec(key=str(key), canonical=canonical, aliases=aliases)
    return entities


def _parse_strategies(raw: dict[str, Any]) -> dict[str, StrategySpec]:
    strategies: dict[str, StrategySpec] = {}
    for name, value in raw.items():
        if not isinstance(value, dict):
            raise QueryRulesRegistryError(f"Invalid strategy entry for {name}")
        strategies[str(name)] = StrategySpec(
            name=str(name),
            sparse_weight_multiplier=float(value.get("sparse_weight_multiplier", 1.0)),
            dense_weight_multiplier=float(value.get("dense_weight_multiplier", 1.0)),
            metadata_bonus_multiplier=float(value.get("metadata_bonus_multiplier", 1.0)),
            rerank_top_n=int(value.get("rerank_top_n", 20)),
            retrieval_depth_multiplier=float(value.get("retrieval_depth_multiplier", 1.0)),
        )
    return strategies


def load_query_rules(registry_path: str | Path | None = None) -> QueryRulesRegistry:
    """Load query intelligence rules from JSON."""
    path = Path(registry_path) if registry_path is not None else DEFAULT_RULES_PATH
    if not path.exists():
        raise QueryRulesRegistryError(f"Query rules registry not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return QueryRulesRegistry(
        acronyms=_normalize_mapping(payload.get("acronyms", {})),
        synonyms=_normalize_mapping(payload.get("synonyms", {})),
        entities=_parse_entities(payload.get("entities", {})),
        multi_query_variants=_normalize_mapping(payload.get("multi_query_variants", {})),
        strategies=_parse_strategies(payload.get("strategies", {})),
    )


@lru_cache
def get_query_rules(registry_path: str) -> QueryRulesRegistry:
    return load_query_rules(registry_path)


def get_rules(registry_path: str | Path | None = None) -> QueryRulesRegistry:
    path = str(Path(registry_path) if registry_path is not None else DEFAULT_RULES_PATH)
    return get_query_rules(path)
