#!/usr/bin/env python3
"""Unified benchmark runner for retrieval and embedding evaluation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


def _run_retrieval(extra_argv: list[str]) -> int:
    from app.evaluation.benchmark import main as retrieval_main

    sys.argv = ["benchmark", *extra_argv]
    return retrieval_main()


def _run_embedding(extra_argv: list[str]) -> int:
    from app.evaluation.embedding_benchmark import main as embedding_main

    sys.argv = ["embedding_benchmark", *extra_argv]
    return embedding_main()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run retrieval or embedding benchmarks.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--retrieval",
        action="store_true",
        help="Run 144-case retrieval benchmark (default).",
    )
    mode.add_argument(
        "--embedding",
        action="store_true",
        help="Run embedding model comparison benchmark.",
    )
    mode.add_argument(
        "--hybrid",
        action="store_true",
        help="Run retrieval benchmark (hybrid enabled by default).",
    )
    mode.add_argument(
        "--reranker",
        action="store_true",
        help="Run retrieval benchmark with reranking enabled.",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Run retrieval benchmark with full 144-case dataset.",
    )
    args, extra = parser.parse_known_args(argv)

    if args.embedding:
        return _run_embedding(extra)

    if args.hybrid:
        os.environ.setdefault("HYBRID_ENABLED", "true")
        if "--label" not in extra:
            extra = ["--label", "hybrid_benchmark", *extra]
        return _run_retrieval(extra)

    if args.reranker:
        os.environ.setdefault("RERANKING_ENABLED", "true")
        if "--label" not in extra:
            extra = ["--label", "reranker_benchmark", *extra]
        return _run_retrieval(extra)

    if args.full:
        if "--label" not in extra:
            extra = ["--label", "full_benchmark", *extra]
        return _run_retrieval(extra)

    # Default: --retrieval
    return _run_retrieval(extra)


if __name__ == "__main__":
    raise SystemExit(main())
