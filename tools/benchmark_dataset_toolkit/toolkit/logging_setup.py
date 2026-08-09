"""Logging configuration for console + conversion.log."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(
    *,
    log_file: Path,
    level: str = "INFO",
    console_format: str = "%(levelname)s %(message)s",
    file_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    verbose: bool = False,
) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG if verbose else getattr(logging, level.upper(), logging.INFO))

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(logging.Formatter(console_format))
    root.addHandler(console)

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_format))
    root.addHandler(file_handler)

    logging.getLogger("toolkit").debug("Logging initialized → %s", log_file)
