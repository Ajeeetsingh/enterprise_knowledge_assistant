"""Measure approximate query-router overhead (dev regression aid).

Usage (from backend/ with PYTHONPATH set):
  python scripts/measure_query_router_perf.py

Does not print secrets. Safe to run locally.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from app.query_router.knowledge_classifier import KnowledgeRouteClassifier
from app.query_router.product_matcher import ProductIntentMatcher
from app.query_router.router import QueryRouter
from app.query_router.types import UserQueryContext


def _ms(fn, n: int = 20) -> float:
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - start) * 1000 / n


def main() -> None:
    ctx = UserQueryContext("Employee", False, True, 1)
    ctx0 = UserQueryContext("Employee", False, False, 0)

    product_matcher = ProductIntentMatcher()
    # Cold semantic warm-up (shared embedding manager).
    product_matcher.match("What can this assistant help me with?")

    product_router = QueryRouter(product_matcher=product_matcher, llm_provider=False)
    mock_matcher = MagicMock()
    mock_matcher.match_and_answer.return_value = None
    det_router = QueryRouter(product_matcher=mock_matcher, llm_provider=False)

    exact_ms = _ms(lambda: product_router.route("What can you do?", ctx0))
    # Semantic warm path — paraphrase unlikely to be exact.
    semantic_ms = _ms(
        lambda: product_matcher.match("Could you tell me how you assist employees?")
    )
    doc_ms = _ms(lambda: det_router.route("What is our leave policy?", ctx))
    gen_ms = _ms(lambda: det_router.route("Explain EBITDA.", ctx))
    zero_doc_ms = _ms(
        lambda: det_router.route("What is our annual leave policy?", ctx0)
    )

    # Ambiguous without LLM (safe document default).
    amb_ms = _ms(lambda: det_router.route("Tell me more.", ctx))

    print("Query router overhead (avg ms / call, n=20)")
    print(f"  exact PRODUCT_HELP:           {exact_ms:.2f}")
    print(f"  semantic product match warm:  {semantic_ms:.2f}")
    print(f"  deterministic DOCUMENT:       {doc_ms:.2f}")
    print(f"  deterministic GENERAL:        {gen_ms:.2f}")
    print(f"  ambiguous default DOCUMENT:   {amb_ms:.2f}")
    print(f"  zero-doc DOCUMENT short-circ:  {zero_doc_ms:.2f}")

    # Confirm embedding manager is shared (same object id).
    from app.embeddings.manager import get_embedding_manager

    m1 = product_matcher._get_embedding_manager()
    m2 = get_embedding_manager()
    print(f"  shared embedding manager:     {m1 is m2}")
    print(f"  product example vectors cached:{product_matcher._example_vectors is not None}")


if __name__ == "__main__":
    main()
