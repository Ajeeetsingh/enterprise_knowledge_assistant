"""Report writers and console summary."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from toolkit.models import ConversionReport, ConversionResult, ConversionStatus

logger = logging.getLogger(__name__)


def format_elapsed(seconds: float) -> str:
    total = int(round(seconds))
    return str(timedelta(seconds=total))


def write_json_report(report: ConversionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    logger.info("Wrote report → %s", path)


def write_failures_report(results: list[ConversionResult], path: Path) -> None:
    failures = [r.to_dict() for r in results if r.status == ConversionStatus.FAILED]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump({"failed_count": len(failures), "failures": failures}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    logger.info("Wrote failures report → %s (%s)", path, len(failures))


def print_summary(
    report: ConversionReport,
    *,
    project_name: str,
    manifest_path: Path | None = None,
) -> None:
    line = "-" * 39
    print()
    print(line)
    print(project_name)
    print(line)
    print(f"Markdown files discovered : {report.total_files}")
    print(f"Converted                 : {report.success}")
    print(f"Skipped                   : {report.skipped}")
    print(f"Failed                    : {report.failed}")
    if report.dry_run:
        print(f"Dry-run planned           : {report.dry_run}")
    print(f"Verified OK               : {report.verified_ok}")
    print(f"Elapsed                   : {format_elapsed(report.elapsed_seconds)}")
    print(f"Avg conversion time       : {report.average_conversion_seconds:.3f}s")
    print(f"Output                    :")
    print(f"  {report.output_dir}")
    if manifest_path is not None:
        print(f"Manifest                  :")
        print(f"  {manifest_path}")
    print(line)
    print()
