"""Command-line interface for the Knowra Benchmark Dataset Toolkit."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from toolkit import __version__
from toolkit.config import DEFAULT_CONFIG_PATH, ToolkitConfig
from toolkit.converters.registry import get_default_registry
from toolkit.logging_setup import setup_logging
from toolkit.pipeline import ConversionPipeline
from toolkit.utils.pandoc import PandocNotFoundError

logger = logging.getLogger(__name__)


def _repo_root_from_toolkit() -> Path:
    return Path(__file__).resolve().parents[3]


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help=f"Path to config.yaml (default: {DEFAULT_CONFIG_PATH})",
)
@click.option(
    "--input",
    "input_dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Input directory containing Markdown files.",
)
@click.option(
    "--output",
    "output_dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Output directory for generated PDFs.",
)
@click.option(
    "--workers",
    type=click.IntRange(min=1, max=64),
    default=None,
    help="Parallel worker count.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Reconvert even when the target PDF already exists.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Discover and plan conversions without writing PDFs.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.option(
    "--converter",
    "converter_name",
    type=str,
    default="markdown_to_pdf",
    show_default=True,
    help="Registered converter name.",
)
@click.version_option(__version__, prog_name="Knowra Benchmark Dataset Toolkit")
def main(
    config_path: Path | None,
    input_dir: Path | None,
    output_dir: Path | None,
    workers: int | None,
    force: bool,
    dry_run: bool,
    verbose: bool,
    converter_name: str,
) -> None:
    """Convert the Apex National Bank Markdown benchmark corpus to PDFs."""
    try:
        config = ToolkitConfig.load(config_path, repo_root=_repo_root_from_toolkit())
        config = config.with_overrides(
            input_dir=input_dir,
            output_dir=output_dir,
            workers=workers,
            force=force,
        )

        # Ensure log directory exists before handlers attach
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        setup_logging(
            log_file=config.log_file,
            level="DEBUG" if verbose else config.log_level,
            console_format=config.console_format,
            file_format=config.file_format,
            verbose=verbose,
        )

        registry = get_default_registry()
        converter = registry.get(converter_name)

        pipeline = ConversionPipeline(
            config,
            converter,
            force=force,
            dry_run=dry_run,
            verbose=verbose,
        )
        report = pipeline.run()
        code = 1 if report.failed else 0
        sys.exit(code)
    except (FileNotFoundError, KeyError, PandocNotFoundError) as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Fatal error")
        click.echo(f"FATAL: {exc}", err=True)
        sys.exit(2)


if __name__ == "__main__":
    main(standalone_mode=True)
