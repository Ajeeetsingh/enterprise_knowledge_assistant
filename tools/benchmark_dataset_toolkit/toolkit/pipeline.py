"""Conversion pipeline orchestrator (parallel, resumable, report-emitting)."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from toolkit.config import ToolkitConfig
from toolkit.converters.base import BaseConverter, ConverterContext
from toolkit.manifest import build_and_write_manifest, default_manifest_path
from toolkit.models import ConversionJob, ConversionReport, ConversionResult, ConversionStatus
from toolkit.reporting import print_summary, write_failures_report, write_json_report
from toolkit import __version__

logger = logging.getLogger(__name__)


class ConversionPipeline:
    """Run a registered converter across a discovered job set."""

    def __init__(
        self,
        config: ToolkitConfig,
        converter: BaseConverter,
        *,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        self.config = config
        self.converter = converter
        self.force = force
        self.dry_run = dry_run
        self.verbose = verbose

    def run(self) -> ConversionReport:
        started = time.perf_counter()
        context = ConverterContext(
            config=self.config,
            force=self.force,
            dry_run=self.dry_run,
            verbose=self.verbose,
        )

        if not self.dry_run:
            # Fail fast if pandoc / PDF engine missing (when converter supports it)
            ensure = getattr(self.converter, "ensure_dependencies", None)
            if callable(ensure):
                ensure()
            ensure_engine = getattr(self.converter, "ensure_pdf_engine", None)
            if callable(ensure_engine):
                ensure_engine(self.config.pdf_engine)

        jobs = self.converter.build_jobs(self.config)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting %s | jobs=%s workers=%s force=%s dry_run=%s",
            self.converter.name,
            len(jobs),
            self.config.workers,
            self.force,
            self.dry_run,
        )

        results = self._execute(jobs, context)
        elapsed = time.perf_counter() - started
        report = self._build_report(jobs, results, elapsed)

        write_json_report(report, self.config.report_json)
        write_failures_report(results, self.config.failures_json)

        # Validate PDFs (already done per-result) → emit evaluation manifest.
        manifest_path = None
        if not self.dry_run:
            try:
                manifest_path = build_and_write_manifest(
                    results,
                    output_dir=self.config.output_dir,
                    strip_prefix=self.config.strip_prefix,
                    manifest_path=default_manifest_path(
                        self.config.output_dir, self.config.repo_root
                    ),
                )
            except Exception as exc:  # noqa: BLE001 — manifest must never abort conversion
                logger.error("Failed to write dataset_manifest.json: %s", exc)

        # Flush logging handlers so the banner is not interleaved with late log lines.
        for handler in logging.getLogger().handlers:
            handler.flush()
        print_summary(
            report,
            project_name=self.config.project_name,
            manifest_path=manifest_path,
        )
        return report

    def _execute(self, jobs: list[ConversionJob], context: ConverterContext) -> list[ConversionResult]:
        if not jobs:
            return []

        results: list[ConversionResult] = []
        workers = max(1, self.config.workers)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            transient=False,
        ) as progress:
            task_id = progress.add_task("Converting", total=len(jobs))

            if workers == 1 or self.dry_run:
                for job in jobs:
                    result = self.converter.convert_one(job, context)
                    results.append(result)
                    self._log_result(result, len(results), len(jobs))
                    progress.advance(task_id)
                return results

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self.converter.convert_one, job, context): job for job in jobs
                }
                for future in as_completed(futures):
                    job = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:  # noqa: BLE001 — isolate worker faults
                        logger.exception("Unhandled worker error for %s", job.source)
                        result = ConversionResult(
                            job=job,
                            status=ConversionStatus.FAILED,
                            error=f"Unhandled: {exc}",
                        )
                        if not self.config.continue_on_error:
                            raise
                    results.append(result)
                    self._log_result(result, len(results), len(jobs))
                    progress.advance(task_id)

        # Stable order by relative source
        results.sort(key=lambda r: str(r.job.relative_source).lower())
        return results

    def _log_result(self, result: ConversionResult, done: int, total: int) -> None:
        rel = str(result.job.relative_source).replace("\\", "/")
        if result.status == ConversionStatus.SUCCESS:
            logger.info("[%s / %s] OK   %s", done, total, rel)
        elif result.status == ConversionStatus.SKIPPED:
            logger.info("[%s / %s] SKIP %s", done, total, rel)
        elif result.status == ConversionStatus.DRY_RUN:
            logger.info("[%s / %s] PLAN %s → %s", done, total, rel, result.job.target.name)
        else:
            logger.error("[%s / %s] FAIL %s — %s", done, total, rel, result.error)

    def _build_report(
        self,
        jobs: list[ConversionJob],
        results: list[ConversionResult],
        elapsed: float,
    ) -> ConversionReport:
        success = sum(1 for r in results if r.status == ConversionStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == ConversionStatus.FAILED)
        skipped = sum(1 for r in results if r.status == ConversionStatus.SKIPPED)
        dry = sum(1 for r in results if r.status == ConversionStatus.DRY_RUN)
        verified_ok = sum(1 for r in results if r.verified)
        verified_failed = sum(
            1
            for r in results
            if r.status == ConversionStatus.SUCCESS and not r.verified
        )

        timed = [r.elapsed_seconds for r in results if r.status == ConversionStatus.SUCCESS]
        avg = sum(timed) / len(timed) if timed else 0.0

        errors = [
            {
                "source": str(r.job.source),
                "target": str(r.job.target),
                "error": r.error,
            }
            for r in results
            if r.status == ConversionStatus.FAILED
        ]

        return ConversionReport(
            toolkit=f"knowra-benchmark-dataset-toolkit@{__version__}",
            converter=self.converter.name,
            input_dir=str(self.config.input_dir),
            output_dir=str(self.config.output_dir),
            total_files=len(jobs),
            success=success,
            failed=failed,
            skipped=skipped,
            dry_run=dry,
            elapsed_seconds=round(elapsed, 3),
            average_conversion_seconds=round(avg, 4),
            workers=self.config.workers,
            force=self.force,
            dry_run_mode=self.dry_run,
            verified_ok=verified_ok,
            verified_failed=verified_failed,
            errors=errors,
            results=[r.to_dict() for r in results],
        )
