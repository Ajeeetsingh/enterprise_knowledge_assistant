"""Semantic enterprise-document intent matching (tenant-agnostic).

Uses generic prototypes about organizational knowledge — never customer-specific
document titles or bank names. Mirrors ProductIntentMatcher embedding reuse.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

from app.core.logging import get_logger
from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager

logger = get_logger(__name__)

# Sentinel stored in the query cache for negative matches.
_CACHE_MISS = object()

# Cosine threshold for MiniLM short-text similarity against generic prototypes.
# Tuned on MiniLM short-text scores: enterprise mission-style questions ~0.66+,
# pure general concepts (EBITDA / Python) stay well below ~0.30.
DEFAULT_ENTERPRISE_INTENT_THRESHOLD = 0.64

# Tenant-agnostic prototypes: "should this be answered from uploaded enterprise docs?"
ENTERPRISE_DOCUMENT_PROTOTYPES: tuple[str, ...] = (
    "What is the company's mission vision and core values?",
    "What are our organization's ethical principles?",
    "Explain the organization's knowledge classification hierarchy",
    "What categories of metadata are defined in our internal standards?",
    "Describe the committee governance structure",
    "Explain our internal metadata standards",
    "What do our company documents say about approval authority?",
    "Describe document naming and versioning rules",
    "What is the internal approval authority matrix?",
    "What is the records retention policy?",
    "Summarize the employee handbook leave policy",
    "What are the organization's internal policies and procedures?",
    "Explain how business processes are classified internally",
    "Who approves this according to the governance documents?",
    "What does our internal documentation say about this topic?",
    "Describe the roles and responsibilities in our org chart documents",
)


@dataclass(frozen=True)
class EnterpriseIntentMatch:
    """Semantic match against a generic enterprise-document prototype."""

    confidence: float
    prototype: str
    method: str = "semantic_enterprise_intent"


class EnterpriseIntentMatcher:
    """Detect when a question is likely about uploaded enterprise knowledge."""

    def __init__(
        self,
        prototypes: tuple[str, ...] = ENTERPRISE_DOCUMENT_PROTOTYPES,
        *,
        embedding_manager: EmbeddingModelManager | None = None,
        threshold: float = DEFAULT_ENTERPRISE_INTENT_THRESHOLD,
    ) -> None:
        self._prototypes = prototypes
        self._embedding_manager = embedding_manager
        self._threshold = threshold
        self._lock = threading.Lock()
        self._vectors: np.ndarray | None = None
        self._labels: list[str] | None = None
        self._query_cache: dict[str, EnterpriseIntentMatch | object] = {}

    def _manager(self) -> EmbeddingModelManager:
        if self._embedding_manager is None:
            self._embedding_manager = get_embedding_manager()
        return self._embedding_manager

    def _ensure_index(self) -> tuple[np.ndarray, list[str]]:
        if self._vectors is not None and self._labels is not None:
            return self._vectors, self._labels
        with self._lock:
            if self._vectors is not None and self._labels is not None:
                return self._vectors, self._labels
            labels = [p.strip() for p in self._prototypes if p.strip()]
            if not labels:
                empty = np.zeros((0, 1), dtype=np.float32)
                self._vectors = empty
                self._labels = []
                return empty, []
            matrix = np.asarray(self._manager().encode(labels), dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.clip(norms, 1e-12, None)
            self._vectors = matrix / norms
            self._labels = labels
            return self._vectors, self._labels

    def match(self, query: str) -> EnterpriseIntentMatch | None:
        """Return a match when *query* is semantically about enterprise documents."""
        cleaned = (query or "").strip()
        if not cleaned:
            return None

        cache_key = cleaned.lower()
        with self._lock:
            cached = self._query_cache.get(cache_key)
        if cached is not None:
            return cached if cached is not _CACHE_MISS else None

        result = self._match_uncached(cleaned)
        with self._lock:
            if len(self._query_cache) >= 256:
                self._query_cache.clear()
            self._query_cache[cache_key] = result if result is not None else _CACHE_MISS
        return result

    def _match_uncached(self, cleaned: str) -> EnterpriseIntentMatch | None:
        try:
            vectors, labels = self._ensure_index()
        except Exception as exc:  # noqa: BLE001 — fail-open
            logger.warning("Enterprise intent embeddings unavailable: %s", type(exc).__name__)
            return None
        if vectors.size == 0 or not labels:
            return None

        try:
            query_vec = np.asarray(self._manager().encode([cleaned]), dtype=np.float32)[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Enterprise intent encode failed: %s", type(exc).__name__)
            return None

        norm = float(np.linalg.norm(query_vec))
        if norm < 1e-12:
            return None
        query_vec = query_vec / norm
        scores = vectors @ query_vec
        best_idx = int(np.argmax(scores))
        best = float(scores[best_idx])
        if best < self._threshold:
            return None
        return EnterpriseIntentMatch(
            confidence=round(best, 4),
            prototype=labels[best_idx],
        )


_matcher: EnterpriseIntentMatcher | None = None
_matcher_lock = threading.Lock()


def get_enterprise_intent_matcher() -> EnterpriseIntentMatcher:
    """Process-wide matcher singleton."""
    global _matcher
    if _matcher is None:
        with _matcher_lock:
            if _matcher is None:
                _matcher = EnterpriseIntentMatcher()
    return _matcher
