#!/usr/bin/env python3
"""Orchestrate common Knowra benchmark conversion workflows.

Reuses the existing toolkit pipeline — no conversion logic is duplicated.

Examples
--------
    python run_benchmark_conversion.py --sample
    python run_benchmark_conversion.py --domain 03_finance
    python run_benchmark_conversion.py --domain 11_customer_cases/case_003_aml_investigation
    python run_benchmark_conversion.py --all --workers 8 --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLKIT_HOME = Path(__file__).resolve().parent
if str(_TOOLKIT_HOME) not in sys.path:
    sys.path.insert(0, str(_TOOLKIT_HOME))

from toolkit.config import ToolkitConfig  # noqa: E402
from toolkit.converters.registry import get_default_registry  # noqa: E402
from toolkit.discovery import build_jobs  # noqa: E402
from toolkit.logging_setup import setup_logging  # noqa: E402
from toolkit.manifest import default_manifest_path  # noqa: E402
from toolkit.pipeline import ConversionPipeline  # noqa: E402


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _first_markdown(folder: Path) -> Path | None:
    files = sorted(
        p for p in folder.glob("*.md") if p.is_file() and not p.name.startswith(("_", "."))
    )
    return files[0].resolve() if files else None


def select_sample(input_dir: Path) -> list[Path]:
    """First Markdown per top-level domain; first per customer case folder."""
    selected: list[Path] = []
    domains = sorted(
        p for p in input_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))
    )
    for domain in domains:
        case_dirs = sorted(
            p for p in domain.iterdir() if p.is_dir() and p.name.startswith("case_")
        )
        if case_dirs:
            for case_dir in case_dirs:
                first = _first_markdown(case_dir)
                if first is not None:
                    selected.append(first)
            continue
        first = _first_markdown(domain)
        if first is not None:
            selected.append(first)
    return selected


def select_domain(input_dir: Path, domain: str) -> list[Path]:
    """All Markdown files under a domain (or nested case) path."""
    target = (input_dir / domain).resolve()
    try:
        target.relative_to(input_dir.resolve())
    except ValueError as exc:
        raise SystemExit(f"ERROR: domain path escapes input root: {domain}") from exc
    if not target.exists():
        raise SystemExit(f"ERROR: domain path not found: {target}")
    if target.is_file():
        if target.suffix.lower() != ".md":
            raise SystemExit(f"ERROR: not a Markdown file: {target}")
        return [target]
    files = sorted(
        p.resolve()
        for p in target.rglob("*.md")
        if p.is_file() and not p.name.startswith((".", "_"))
    )
    if not files:
        raise SystemExit(f"ERROR: no Markdown files under {target}")
    return files


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate Knowra benchmark Markdown → PDF conversions.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--sample",
        action="store_true",
        help="Convert one validation document per domain / customer case.",
    )
    mode.add_argument(
        "--domain",
        metavar="PATH",
        help="Convert Markdown under a domain path (relative to dataset root).",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="Convert the entire benchmark dataset.",
    )
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers.")
    parser.add_argument("--force", action="store_true", help="Reconvert existing PDFs.")
    parser.add_argument("--verbose", action="store_true", help="Debug logging.")
    return parser.parse_args(argv)


def _mode_label(args: argparse.Namespace) -> str:
    if args.sample:
        return "SAMPLE"
    if args.domain:
        return f"DOMAIN ({args.domain})"
    return "ALL"


def _print_wrapper_summary(
    *,
    mode: str,
    discovered: int,
    converted: int,
    failed: int,
    skipped: int,
    manifest: Path | None,
) -> None:
    print()
    print(f"Mode: {mode}")
    print(f"Documents discovered: {discovered}")
    print(f"Converted: {converted}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print("Manifest:")
    print(f"  {manifest if manifest is not None else '(not written)'}")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    config = ToolkitConfig.load(repo_root=_repo_root())
    config = config.with_overrides(workers=args.workers, force=args.force)

    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(
        log_file=config.log_file,
        level="DEBUG" if args.verbose else config.log_level,
        console_format=config.console_format,
        file_format=config.file_format,
        verbose=args.verbose,
    )

    if args.sample:
        sources: list[Path] | None = select_sample(config.input_dir)
    elif args.domain:
        sources = select_domain(config.input_dir, args.domain)
    else:
        sources = None  # full discovery via toolkit

    converter = get_default_registry().get("markdown_to_pdf")
    if sources is not None:
        selected = list(sources)

        def _filtered_build_jobs(cfg: ToolkitConfig):
            return build_jobs(cfg, selected)

        converter.build_jobs = _filtered_build_jobs  # type: ignore[method-assign]

    pipeline = ConversionPipeline(
        config,
        converter,
        force=args.force,
        dry_run=False,
        verbose=args.verbose,
    )
    report = pipeline.run()

    manifest = default_manifest_path(config.output_dir, config.repo_root)
    if not manifest.is_file():
        manifest = None

    _print_wrapper_summary(
        mode=_mode_label(args),
        discovered=report.total_files,
        converted=report.success,
        failed=report.failed,
        skipped=report.skipped,
        manifest=manifest,
    )
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
