"""Markdown → PDF converter powered by Pandoc (+ Chrome/Edge or TeX engines)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import ClassVar

from toolkit.converters.base import BaseConverter, ConverterContext
from toolkit.models import ConversionJob, ConversionResult, ConversionStatus
from toolkit.pdf_enhance import enhance_and_validate_pdf
from toolkit.utils.pandoc import PandocError, PandocNotFoundError, find_pandoc, run_pandoc
from toolkit.utils.paths import ensure_parent
from toolkit.validation import verify_pdf

logger = logging.getLogger(__name__)

_LATEX_ENGINES = frozenset({"xelatex", "lualatex", "pdflatex", "latex", "context", "tectonic"})
_BROWSER_ENGINES = frozenset({"chrome", "edge", "chromium", "msedge"})


def _resolve_browser(engine: str) -> str | None:
    """Locate Chrome/Edge for headless print-to-PDF."""
    names = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "chrome",
            "google-chrome",
        ],
        "chromium": ["chromium", "chromium-browser", "chrome"],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge",
            "microsoft-edge",
        ],
        "msedge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge",
        ],
    }
    for candidate in names.get(engine.lower(), [engine]):
        path = Path(candidate)
        if path.is_file():
            return str(path)
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _resolve_engine_path(engine: str) -> str | None:
    if engine.lower() in _BROWSER_ENGINES:
        return _resolve_browser(engine)
    which = shutil.which(engine)
    if which:
        return which
    if engine == "weasyprint":
        scripts = Path(sys.executable).resolve().parent
        for name in ("weasyprint.exe", "weasyprint"):
            candidate = scripts / name
            if candidate.is_file():
                return str(candidate)
    return None


class MarkdownToPdfConverter(BaseConverter):
    name: ClassVar[str] = "markdown_to_pdf"
    description: ClassVar[str] = "Convert Markdown documents to enterprise-quality PDFs via Pandoc"
    source_suffix: ClassVar[str] = ".md"
    target_suffix: ClassVar[str] = ".pdf"

    def __init__(self) -> None:
        self._pandoc_path: str | None = None
        self._engine_path: str | None = None

    def ensure_dependencies(self) -> str:
        info = find_pandoc()
        self._pandoc_path = info.path
        logger.info("Using %s", info.version)
        return info.path

    def ensure_pdf_engine(self, engine: str) -> str | None:
        path = _resolve_engine_path(engine)
        self._engine_path = path
        if path:
            logger.info("Using PDF engine %s → %s", engine, path)
        else:
            logger.warning("PDF engine '%s' not found on PATH", engine)
        return path

    def convert_one(self, job: ConversionJob, context: ConverterContext) -> ConversionResult:
        cfg = context.config
        started = time.perf_counter()

        if context.dry_run:
            return ConversionResult(
                job=job,
                status=ConversionStatus.DRY_RUN,
                elapsed_seconds=time.perf_counter() - started,
            )

        if job.target.exists() and cfg.skip_existing and not context.force:
            verified = self.verify_target(job.target, context)
            return ConversionResult(
                job=job,
                status=ConversionStatus.SKIPPED,
                elapsed_seconds=time.perf_counter() - started,
                verified=verified,
            )

        try:
            pandoc = self._pandoc_path or self.ensure_dependencies()
            ensure_parent(job.target)
            engine = cfg.pdf_engine.lower()
            if engine in _BROWSER_ENGINES:
                self._convert_via_browser(pandoc, job.source, job.target, context)
            else:
                args = self._build_pandoc_args(pandoc, job.source, job.target, context)
                run_pandoc(args)

            verified = self.verify_target(job.target, context)
            if not verified:
                return ConversionResult(
                    job=job,
                    status=ConversionStatus.FAILED,
                    elapsed_seconds=time.perf_counter() - started,
                    error="PDF failed post-conversion verification",
                    verified=False,
                )

            # Enterprise header/footer/metadata — warnings only, never fail conversion
            try:
                enhance_and_validate_pdf(
                    job.target,
                    markdown_path=job.source,
                    config=cfg,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Enterprise PDF enhance skipped for %s: %s", job.source.name, exc)

            return ConversionResult(
                job=job,
                status=ConversionStatus.SUCCESS,
                elapsed_seconds=time.perf_counter() - started,
                verified=True,
            )
        except (PandocNotFoundError, PandocError, OSError, TimeoutError, RuntimeError) as exc:
            logger.error("Failed %s → %s: %s", job.source.name, job.target.name, exc)
            return ConversionResult(
                job=job,
                status=ConversionStatus.FAILED,
                elapsed_seconds=time.perf_counter() - started,
                error=str(exc),
                verified=False,
            )

    def verify_target(self, path: Path, context: ConverterContext) -> bool:
        return verify_pdf(
            path,
            min_bytes=context.config.min_bytes,
            check_magic=context.config.verify_pdf_magic,
        )

    def _convert_via_browser(
        self,
        pandoc: str,
        source: Path,
        target: Path,
        context: ConverterContext,
    ) -> None:
        """Pandoc Markdown → HTML, then Chrome/Edge headless print-to-PDF."""
        cfg = context.config
        browser = self._engine_path or self.ensure_pdf_engine(cfg.pdf_engine)
        if not browser:
            raise RuntimeError(
                f"Browser PDF engine '{cfg.pdf_engine}' not found. "
                "Install Google Chrome or Microsoft Edge, or set pdf_engine to xelatex."
            )

        css = cfg.toolkit_root / "assets" / "pandoc" / "print.css"
        with tempfile.TemporaryDirectory(prefix="knowra_pdf_") as tmp:
            html_path = Path(tmp) / f"{source.stem}.html"
            args = [
                pandoc,
                str(source),
                "-o",
                str(html_path),
                f"--from={cfg.from_format}",
                "--to=html5",
                "--standalone",
                f"--syntax-highlighting={cfg.syntax_highlighting}",
                f"--resource-path={source.parent}",
                f"--metadata=title={source.stem}",
            ]
            if cfg.toc:
                args.append("--toc")
                args.append(f"--toc-depth={cfg.toc_depth}")
            if css.is_file():
                args.extend([f"--css={css}"])
            # Pandoc HTML5 TOC entries are anchor links; Chrome preserves them when toc_links is on.
            args.extend(cfg.extra_args)
            run_pandoc(args)

            html_uri = html_path.resolve().as_uri()
            cmd = [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={target.resolve()}",
                html_uri,
            ]
            logger.debug("Running: %s", " ".join(cmd))
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if completed.returncode != 0 or not target.is_file():
                detail = (completed.stderr or completed.stdout or "").strip()
                raise RuntimeError(
                    f"Browser PDF engine failed (exit {completed.returncode}): {detail[:1500]}"
                )

    def _build_pandoc_args(
        self,
        pandoc: str,
        source: Path,
        target: Path,
        context: ConverterContext,
    ) -> list[str]:
        cfg = context.config
        engine = cfg.pdf_engine
        args: list[str] = [
            pandoc,
            str(source),
            "-o",
            str(target),
            f"--from={cfg.from_format}",
            f"--pdf-engine={engine}",
            f"--syntax-highlighting={cfg.syntax_highlighting}",
            "--standalone",
        ]

        engine_path = self._engine_path or _resolve_engine_path(engine)
        if engine_path and Path(engine_path).is_file():
            args.append(f"--pdf-engine-path={engine_path}")

        if cfg.toc:
            args.append("--toc")
            args.append(f"--toc-depth={cfg.toc_depth}")

        if cfg.number_sections:
            args.append("--number-sections")

        for key, value in cfg.variables.items():
            args.extend(["-V", f"{key}={value}"])

        if (
            cfg.include_header
            and cfg.include_header.is_file()
            and engine.lower() in _LATEX_ENGINES
        ):
            args.extend([f"--include-in-header={cfg.include_header}"])

        args.extend([f"--resource-path={source.parent}"])
        args.extend(cfg.extra_args)
        return args
