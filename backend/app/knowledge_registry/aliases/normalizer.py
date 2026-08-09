"""Canonical category / concept normalization."""

from __future__ import annotations

import re

from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_registry.aliases.catalog import build_alias_lookup

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9 &/+-]{1,}")


class AliasNormalizer:
    """Normalize free-text concepts onto canonical terms."""

    def __init__(self) -> None:
        self._lookup = build_alias_lookup()

    def normalize_knowledge(
        self,
        knowledge: DocumentKnowledge,
    ) -> tuple[list[str], list[dict[str, str]]]:
        texts = [
            *knowledge.topics,
            *knowledge.keywords,
            *knowledge.tags,
            knowledge.metadata.filename,
            knowledge.summary.short,
        ]
        applied: list[dict[str, str]] = []
        canons: list[str] = []
        seen: set[str] = set()

        for raw in texts:
            for match in self._iter_aliases(str(raw)):
                canonical = self._lookup[match]
                applied.append({"alias": match, "canonical": canonical})
                if canonical not in seen:
                    seen.add(canonical)
                    canons.append(canonical)

        # Phrase scan across summary+topics for multi-word aliases.
        blob = " ".join(texts).lower()
        for alias, canonical in self._lookup.items():
            if " " in alias and alias in blob:
                applied.append({"alias": alias, "canonical": canonical})
                if canonical not in seen:
                    seen.add(canonical)
                    canons.append(canonical)
        return canons, applied

    def normalize_term(self, term: str) -> str:
        key = term.strip().lower()
        return self._lookup.get(key, term.strip())

    def _iter_aliases(self, text: str):
        lowered = text.lower()
        if lowered in self._lookup:
            yield lowered
        for token in _TOKEN_RE.findall(lowered):
            token = token.strip()
            if token in self._lookup:
                yield token
