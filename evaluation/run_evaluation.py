#!/usr/bin/env python3
"""Standalone Knowra domain evaluation entrypoint.

Usage:
    python run_evaluation.py human_resources
    python evaluation/run_evaluation.py finance

The domain name must match a folder under docs/test_docs/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow ``python evaluation/run_evaluation.py`` and root shim imports.
_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from config import TEST_DOCS_ROOT, load_settings  # noqa: E402
from evaluator import DomainEvaluator  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Knowra chat evaluation for a domain folder under docs/test_docs/."
        ),
        epilog=(
            "Example:\n"
            "  python run_evaluation.py human_resources\n\n"
            "Configure API access in evaluation/.env "
            "(KNOWRA_ACCESS_TOKEN or KNOWRA_EMAIL / KNOWRA_PASSWORD)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "domain",
        nargs="?",
        default=None,
        help="Folder name inside docs/test_docs/ (e.g. human_resources, finance)",
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="List available domain folders and exit.",
    )
    return parser


def list_domains() -> int:
    if not TEST_DOCS_ROOT.is_dir():
        print(f"No test docs root found at: {TEST_DOCS_ROOT}")
        return 1
    domains = sorted(
        path.name
        for path in TEST_DOCS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if not domains:
        print(f"No domain folders found under {TEST_DOCS_ROOT}")
        return 1
    print("Available domains:")
    for name in domains:
        has_questions = (TEST_DOCS_ROOT / name / "questions.txt").is_file()
        marker = "ok" if has_questions else "missing questions.txt"
        print(f"  - {name} ({marker})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_domains:
        return list_domains()

    if not args.domain:
        parser.error("domain is required (or pass --list-domains)")

    domain = str(args.domain).strip()
    if not domain or domain in {".", ".."} or "/" in domain or "\\" in domain:
        print(
            "Invalid domain name. Pass a single folder name "
            "(e.g. human_resources), not a path."
        )
        return 2

    try:
        settings = load_settings()
        evaluator = DomainEvaluator(domain_name=domain, settings=settings)
        summary = evaluator.run()
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130

    return 0 if summary.failed_requests == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
