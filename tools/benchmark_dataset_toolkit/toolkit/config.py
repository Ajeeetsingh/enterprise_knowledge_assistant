"""Load and resolve toolkit configuration from config.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = TOOLKIT_ROOT / "config.yaml"


@dataclass(slots=True)
class ToolkitConfig:
    raw: dict[str, Any]
    config_path: Path
    toolkit_root: Path
    repo_root: Path
    input_dir: Path
    output_dir: Path
    strip_prefix: str
    markdown_patterns: list[str]
    exclude_patterns: list[str]
    workers: int
    skip_existing: bool
    continue_on_error: bool
    pdf_engine: str
    from_format: str
    toc: bool
    toc_depth: int
    number_sections: bool
    syntax_highlighting: str
    variables: dict[str, str]
    include_header: Path | None
    extra_args: list[str]
    header_enabled: bool
    footer_enabled: bool
    page_numbers: bool
    pdf_metadata: bool
    toc_links: bool
    cover_page: bool
    bookmarks: bool
    report_json: Path
    log_file: Path
    failures_json: Path
    verify_pdf_magic: bool
    min_bytes: int
    enterprise_checks: bool
    log_level: str
    console_format: str
    file_format: str
    project_name: str = "Knowra Benchmark Dataset Toolkit"

    @classmethod
    def load(cls, config_path: Path | None = None, *, repo_root: Path | None = None) -> ToolkitConfig:
        path = (config_path or DEFAULT_CONFIG_PATH).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Config not found: {path}")

        with path.open(encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}

        toolkit_root = path.parent
        project = raw.get("project", {})
        dataset = raw.get("dataset", {})
        conversion = raw.get("conversion", {})
        reporting = raw.get("reporting", {})
        validation = raw.get("validation", {})
        logging_cfg = raw.get("logging", {})

        if repo_root is not None:
            root = repo_root.resolve()
        else:
            configured = project.get("repo_root", "../..")
            root = (toolkit_root / configured).resolve()

        input_dir = _resolve_path(root, toolkit_root, dataset.get("input_dir", "docs/apex_national_bank"))
        output_dir = _resolve_path(root, toolkit_root, dataset.get("output_dir", "benchmark/pdf"))

        include_header_raw = conversion.get("include_header")
        include_header: Path | None = None
        if include_header_raw:
            candidate = _resolve_path(root, toolkit_root, include_header_raw)
            include_header = candidate if candidate.is_file() else (toolkit_root / include_header_raw)

        report_json = _resolve_report_path(output_dir, reporting.get("report_json", "conversion_report.json"))
        log_file = _resolve_report_path(output_dir, reporting.get("log_file", "conversion.log"))
        failures_json = _resolve_report_path(
            output_dir, reporting.get("failures_json", "conversion_failures.json")
        )

        variables = {
            str(k): str(v)
            for k, v in (conversion.get("variables") or {}).items()
            if v is not None and str(v).strip() != ""
        }

        return cls(
            raw=raw,
            config_path=path,
            toolkit_root=toolkit_root,
            repo_root=root,
            input_dir=input_dir,
            output_dir=output_dir,
            strip_prefix=str(dataset.get("strip_prefix", "apex_national_bank")),
            markdown_patterns=list(dataset.get("markdown_patterns") or ["**/*.md"]),
            exclude_patterns=list(dataset.get("exclude_patterns") or []),
            workers=int(conversion.get("workers", 4)),
            skip_existing=bool(conversion.get("skip_existing", True)),
            continue_on_error=bool(conversion.get("continue_on_error", True)),
            pdf_engine=str(conversion.get("pdf_engine", "xelatex")),
            from_format=str(conversion.get("from_format", "markdown")),
            toc=bool(conversion.get("toc", True)),
            toc_depth=int(conversion.get("toc_depth", 3)),
            number_sections=bool(conversion.get("number_sections", False)),
            syntax_highlighting=str(conversion.get("syntax_highlighting", "tango")),
            variables=variables,
            include_header=include_header if include_header and include_header.is_file() else None,
            extra_args=[str(a) for a in (conversion.get("extra_args") or [])],
            header_enabled=bool(conversion.get("header_enabled", True)),
            footer_enabled=bool(conversion.get("footer_enabled", True)),
            page_numbers=bool(conversion.get("page_numbers", True)),
            pdf_metadata=bool(conversion.get("pdf_metadata", True)),
            toc_links=bool(conversion.get("toc_links", True)),
            cover_page=bool(conversion.get("cover_page", True)),
            bookmarks=bool(conversion.get("bookmarks", True)),
            report_json=report_json,
            log_file=log_file,
            failures_json=failures_json,
            verify_pdf_magic=bool(validation.get("verify_pdf_magic", True)),
            min_bytes=int(validation.get("min_bytes", 64)),
            enterprise_checks=bool(validation.get("enterprise_checks", True)),
            log_level=str(logging_cfg.get("level", "INFO")),
            console_format=str(logging_cfg.get("console_format", "%(levelname)s %(message)s")),
            file_format=str(
                logging_cfg.get(
                    "file_format",
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                )
            ),
            project_name=str(project.get("name", "Knowra Benchmark Dataset Toolkit")),
        )

    def with_overrides(
        self,
        *,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        workers: int | None = None,
        force: bool = False,
    ) -> ToolkitConfig:
        """Return a shallow-mutated copy with CLI overrides applied."""
        new_input = input_dir.resolve() if input_dir else self.input_dir
        new_output = output_dir.resolve() if output_dir else self.output_dir
        new_workers = workers if workers is not None else self.workers
        skip_existing = False if force else self.skip_existing

        report_json = _rebase_report(self.report_json, self.output_dir, new_output)
        log_file = _rebase_report(self.log_file, self.output_dir, new_output)
        failures_json = _rebase_report(self.failures_json, self.output_dir, new_output)

        return ToolkitConfig(
            raw=self.raw,
            config_path=self.config_path,
            toolkit_root=self.toolkit_root,
            repo_root=self.repo_root,
            input_dir=new_input,
            output_dir=new_output,
            strip_prefix=self.strip_prefix,
            markdown_patterns=list(self.markdown_patterns),
            exclude_patterns=list(self.exclude_patterns),
            workers=new_workers,
            skip_existing=skip_existing,
            continue_on_error=self.continue_on_error,
            pdf_engine=self.pdf_engine,
            from_format=self.from_format,
            toc=self.toc,
            toc_depth=self.toc_depth,
            number_sections=self.number_sections,
            syntax_highlighting=self.syntax_highlighting,
            variables=dict(self.variables),
            include_header=self.include_header,
            extra_args=list(self.extra_args),
            header_enabled=self.header_enabled,
            footer_enabled=self.footer_enabled,
            page_numbers=self.page_numbers,
            pdf_metadata=self.pdf_metadata,
            toc_links=self.toc_links,
            cover_page=self.cover_page,
            bookmarks=self.bookmarks,
            report_json=report_json,
            log_file=log_file,
            failures_json=failures_json,
            verify_pdf_magic=self.verify_pdf_magic,
            min_bytes=self.min_bytes,
            enterprise_checks=self.enterprise_checks,
            log_level=self.log_level,
            console_format=self.console_format,
            file_format=self.file_format,
            project_name=self.project_name,
        )


def _resolve_path(repo_root: Path, toolkit_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    normalized = str(value).replace("\\", "/")
    repo_candidate = (repo_root / path).resolve()
    toolkit_candidate = (toolkit_root / path).resolve()
    # Toolkit-local assets (e.g. pandoc header.tex)
    if normalized.startswith("assets/"):
        return toolkit_candidate if toolkit_candidate.exists() else repo_candidate
    return repo_candidate


def _resolve_report_path(output_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (output_dir / path).resolve()


def _rebase_report(path: Path, old_output: Path, new_output: Path) -> Path:
    try:
        rel = path.relative_to(old_output)
        return (new_output / rel).resolve()
    except ValueError:
        return path
