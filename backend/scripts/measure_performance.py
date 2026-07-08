"""Unified performance measurement utility."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _measure_embedding() -> int:
    from unittest.mock import patch

    from sentence_transformers import SentenceTransformer

    init_count = 0
    init_times: list[float] = []

    def _counting_init(original):
        def wrapper(self, model_name_or_path, *args, **kwargs):
            nonlocal init_count
            init_count += 1
            t0 = time.perf_counter()
            result = original(self, model_name_or_path, *args, **kwargs)
            init_times.append(time.perf_counter() - t0)
            print(f"  [LOAD #{init_count}] {model_name_or_path} took {init_times[-1]:.2f}s")
            return result

        return wrapper

    print("Embedding Load Performance")
    print("=" * 72)

    with patch.object(SentenceTransformer, "__init__", _counting_init(SentenceTransformer.__init__)):
        from app.embeddings.manager import get_embedding_manager
        from app.services.document_service import get_document_service
        from app.services.rag_service import get_rag_service

        get_embedding_manager.cache_clear()
        get_document_service.cache_clear()
        get_rag_service.cache_clear()

        started = time.perf_counter()
        get_embedding_manager().preload()
        print(f"embedding_manager.preload(): {time.perf_counter() - started:.2f}s")

        started = time.perf_counter()
        get_rag_service().initialize()
        print(f"rag_service.initialize(): {time.perf_counter() - started:.2f}s")
        print(f"Total SentenceTransformer loads: {init_count}")
    return 0


def _measure_reranker(*, candidate_counts: str, queries: int, model: str | None) -> int:
    from app.rag.reranking.config import RerankingSettings
    from app.rag.reranking.reranker import CrossEncoderReranker
    from app.rag.types import RetrievalResult

    def _candidate(index: int) -> RetrievalResult:
        return RetrievalResult(
            content=(
                "GlobalTrust Financial Services quarterly report section "
                f"{index} covering revenue, risk, and operational metrics."
            ),
            source="GTFS-FIN-002_Quarterly_Financial_Report_Q1_FY2026.pdf",
            category="finance",
            confidence=0.55,
            chunk_id=f"chunk-{index:03d}",
            page_number=index % 12 + 1,
        )

    settings = RerankingSettings.from_settings()
    if model:
        settings = RerankingSettings(
            enabled=True,
            rerank_top_n=settings.rerank_top_n,
            rerank_model_id=model,
            max_batch_size=settings.max_batch_size,
            max_sequence_length=settings.max_sequence_length,
        )

    reranker = CrossEncoderReranker(settings=settings)
    load_started = time.perf_counter()
    reranker.preload()
    load_ms = round((time.perf_counter() - load_started) * 1000, 2)

    tracemalloc.start()
    query = "What was GlobalTrust quarterly revenue in Q1 FY2026?"
    counts = [int(v.strip()) for v in candidate_counts.split(",") if v.strip()]

    print("Cross-Encoder Reranking Performance")
    print("=" * 72)
    print(f"Model:     {reranker.runtime.model_name}")
    print(f"Device:    {reranker.runtime.device}")
    print(f"Load (ms): {load_ms}")
    print()

    for count in counts:
        latencies: list[float] = []
        for _ in range(queries):
            candidates = [_candidate(i) for i in range(count)]
            started = time.perf_counter()
            reranker.rerank(query, candidates, top_k=min(5, count))
            latencies.append((time.perf_counter() - started) * 1000)
        avg = statistics.mean(latencies)
        throughput = (count / avg) * 1000 if avg else 0.0
        p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies) > 1 else latencies[0]
        print(
            f"Candidates={count:2d}  avg_ms={avg:8.2f}  p95_ms={p95:8.2f}  "
            f"throughput={throughput:8.1f} pairs/s"
        )

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"\nMemory peak: {peak / (1024 * 1024):.2f} MB")
    return 0


def _measure_query(*, iterations: int) -> int:
    from app.rag.query_processing.config import QueryProcessingSettings
    from app.rag.query_processing.processor import QueryProcessor

    samples = [
        "What is HQ?",
        "Who is the CEO?",
        "What was quarterly revenue in Q1?",
        "What related GTFS document is referenced?",
        "What are the VPN security requirements?",
        "What is Project Phoenix?",
    ]
    processor = QueryProcessor(settings=QueryProcessingSettings.from_settings())

    print("Query Intelligence Performance")
    print("=" * 72)
    latencies: list[float] = []
    query_counts: list[int] = []
    for query in samples:
        per_query: list[float] = []
        generated = 0
        for _ in range(iterations):
            started = time.perf_counter()
            outcome = processor.process(query)
            per_query.append((time.perf_counter() - started) * 1000)
            generated = len(outcome.retrieval_queries)
        latencies.extend(per_query)
        query_counts.append(generated)
        print(
            f"{query[:48]:48s}  avg_ms={statistics.mean(per_query):6.3f}  "
            f"queries={generated}"
        )
    print(f"\nOverall avg latency (ms): {statistics.mean(latencies):.3f}")
    print(f"Avg generated queries:    {statistics.mean(query_counts):.2f}")
    return 0


def _measure_retrieval() -> int:
    print("Retrieval latency is measured via the full benchmark:")
    print("  py scripts/benchmark.py --retrieval --label perf_check --llm-provider none --no-compare")
    print("See avg_retrieval_latency_ms in the exported JSON report.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure pipeline component performance.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--embedding", action="store_true", help="Embedding model load cost.")
    mode.add_argument("--retrieval", action="store_true", help="Retrieval latency guidance.")
    mode.add_argument("--reranker", action="store_true", help="Cross-encoder reranking latency.")
    mode.add_argument("--query", action="store_true", help="Query intelligence latency.")
    mode.add_argument("--full", action="store_true", help="Run embedding, query, and reranker probes.")
    parser.add_argument("--candidate-counts", default="5,10,20")
    parser.add_argument("--queries", type=int, default=5)
    parser.add_argument("--model", default=None, help="Reranker model id override.")
    parser.add_argument("--iterations", type=int, default=50, help="Query intelligence iterations.")
    args = parser.parse_args(argv)

    if args.full:
        codes = [
            _measure_embedding(),
            _measure_query(iterations=min(args.iterations, 20)),
            _measure_reranker(
                candidate_counts=args.candidate_counts,
                queries=args.queries,
                model=args.model,
            ),
            _measure_retrieval(),
        ]
        return max(codes)

    if args.embedding:
        return _measure_embedding()
    if args.retrieval:
        return _measure_retrieval()
    if args.reranker:
        return _measure_reranker(
            candidate_counts=args.candidate_counts,
            queries=args.queries,
            model=args.model,
        )
    if args.query:
        return _measure_query(iterations=args.iterations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
