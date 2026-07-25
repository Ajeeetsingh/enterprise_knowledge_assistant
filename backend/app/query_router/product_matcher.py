"""Product-help intent matching via exact normalized text and embeddings.

Reuses the process-wide ``EmbeddingModelManager`` — never loads a second model.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass

import numpy as np

from app.core.logging import get_logger
from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager
from app.query_router.product_intents import PRODUCT_INTENTS, ProductIntent
from app.query_router.product_responses import resolve_product_answer
from app.query_router.types import UserQueryContext

logger = get_logger(__name__)

# Conservative threshold for MiniLM short-text cosine similarity.
# Unrelated organisational questions should stay below this and fall through
# to DOCUMENT_QUERY rather than being misclassified as product help.
DEFAULT_SEMANTIC_THRESHOLD = 0.78

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_query(text: str) -> str:
    """Normalize user text for exact matching (case/space/light punctuation)."""
    lowered = text.strip().lower()
    lowered = _PUNCT_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", lowered).strip()


@dataclass(frozen=True)
class ProductMatch:
    """A matched product intent with similarity confidence."""

    intent: ProductIntent
    confidence: float
    match_type: str  # "exact" | "semantic"


class ProductIntentMatcher:
    """Match queries to curated product intents.

    Matching order:
    1. Normalized exact match against example phrasings.
    2. High-confidence semantic similarity against cached example embeddings.
    """

    def __init__(
        self,
        intents: tuple[ProductIntent, ...] = PRODUCT_INTENTS,
        *,
        embedding_manager: EmbeddingModelManager | None = None,
        semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    ) -> None:
        self._intents = intents
        self._embedding_manager = embedding_manager
        self._semantic_threshold = semantic_threshold
        self._lock = threading.Lock()
        self._exact_index: dict[str, ProductIntent] | None = None
        # Parallel arrays: example embedding rows and owning intent.
        self._example_vectors: np.ndarray | None = None
        self._example_intents: list[ProductIntent] | None = None

    def _get_embedding_manager(self) -> EmbeddingModelManager:
        if self._embedding_manager is None:
            self._embedding_manager = get_embedding_manager()
        return self._embedding_manager

    def _ensure_exact_index(self) -> dict[str, ProductIntent]:
        if self._exact_index is not None:
            return self._exact_index
        with self._lock:
            if self._exact_index is None:
                index: dict[str, ProductIntent] = {}
                for intent in self._intents:
                    for example in intent.examples:
                        key = normalize_query(example)
                        if key:
                            index[key] = intent
                self._exact_index = index
        return self._exact_index

    def _ensure_semantic_index(self) -> tuple[np.ndarray, list[ProductIntent]]:
        if self._example_vectors is not None and self._example_intents is not None:
            return self._example_vectors, self._example_intents

        with self._lock:
            if self._example_vectors is not None and self._example_intents is not None:
                return self._example_vectors, self._example_intents

            examples: list[str] = []
            owners: list[ProductIntent] = []
            for intent in self._intents:
                for example in intent.examples:
                    cleaned = example.strip()
                    if cleaned:
                        examples.append(cleaned)
                        owners.append(intent)

            if not examples:
                empty = np.zeros((0, 1), dtype=np.float32)
                self._example_vectors = empty
                self._example_intents = []
                return empty, []

            vectors = self._get_embedding_manager().encode(examples)
            matrix = np.asarray(vectors, dtype=np.float32)
            # L2-normalize so cosine = dot product.
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.clip(norms, 1e-12, None)
            matrix = matrix / norms
            self._example_vectors = matrix
            self._example_intents = owners
            return matrix, owners

    def match(self, query: str) -> ProductMatch | None:
        """Return the best product-help match, or ``None`` if below threshold."""
        cleaned = query.strip()
        if not cleaned:
            return None

        normalized = normalize_query(cleaned)
        exact_index = self._ensure_exact_index()
        exact_intent = exact_index.get(normalized)
        if exact_intent is not None:
            return ProductMatch(intent=exact_intent, confidence=1.0, match_type="exact")

        try:
            matrix, owners = self._ensure_semantic_index()
        except Exception:
            logger.exception("Product-help semantic index build failed")
            return None

        if matrix.size == 0 or not owners:
            return None

        try:
            query_vec = self._get_embedding_manager().encode([cleaned])
        except Exception:
            logger.exception("Product-help query embedding failed")
            return None

        q = np.asarray(query_vec, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        q_norm = np.linalg.norm(q, axis=1, keepdims=True)
        q = q / np.clip(q_norm, 1e-12, None)
        scores = (matrix @ q.T).reshape(-1)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < self._semantic_threshold:
            return None
        return ProductMatch(
            intent=owners[best_idx],
            confidence=round(best_score, 4),
            match_type="semantic",
        )

    def match_and_answer(
        self,
        query: str,
        context: UserQueryContext,
    ) -> tuple[ProductMatch, str] | None:
        """Match a product intent and resolve a context-aware curated answer."""
        matched = self.match(query)
        if matched is None:
            return None
        answer = resolve_product_answer(matched.intent, context)
        return matched, answer
