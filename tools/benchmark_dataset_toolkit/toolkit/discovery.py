"""Recursive Markdown discovery with exclude patterns."""

from __future__ import annotations

import logging
from pathlib import Path

from toolkit.config import ToolkitConfig
from toolkit.models import ConversionJob
from toolkit.utils.paths import map_markdown_to_pdf_target

logger = logging.getLogger(__name__)


def _is_excluded(path: Path, root: Path, exclude_patterns: list[str]) -> bool:
    rel = path.relative_to(root).as_posix()
    name = path.name
    for pattern in exclude_patterns:
        # Support simple glob semantics against relative posix path and name
        if path.match(pattern) or Path(rel).match(pattern) or Path(name).match(pattern.lstrip("*/")):
            return True
        # Hidden / underscore scratch files
        if pattern in {"**/.*", "**/_*"}:
            if name.startswith(".") or name.startswith("_"):
                return True
    return False


def discover_markdown_files(config: ToolkitConfig) -> list[Path]:
    """Discover all markdown files under the configured input directory."""
    root = config.input_dir
    if not root.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {root}")

    found: set[Path] = set()
    for pattern in config.markdown_patterns:
        for match in root.glob(pattern):
            if match.is_file() and match.suffix.lower() == ".md":
                if _is_excluded(match, root, config.exclude_patterns):
                    logger.debug("Excluding %s", match)
                    continue
                found.add(match.resolve())

    files = sorted(found)
    logger.info("Discovered %s markdown file(s) under %s", len(files), root)
    return files


def build_jobs(config: ToolkitConfig, sources: list[Path] | None = None) -> list[ConversionJob]:
    """Build conversion jobs preserving relative hierarchy."""
    sources = sources if sources is not None else discover_markdown_files(config)
    jobs: list[ConversionJob] = []
    for source in sources:
        relative, target = map_markdown_to_pdf_target(
            source,
            input_dir=config.input_dir,
            output_dir=config.output_dir,
            strip_prefix=config.strip_prefix,
        )
        jobs.append(ConversionJob(source=source, target=target, relative_source=relative))
    return jobs
