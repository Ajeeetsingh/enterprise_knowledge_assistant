"""Pandoc subprocess helpers."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PandocInfo:
    path: str
    version: str


class PandocNotFoundError(RuntimeError):
    """Raised when the pandoc executable cannot be located."""


class PandocError(RuntimeError):
    """Raised when a pandoc invocation fails."""

    def __init__(self, message: str, *, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def find_pandoc(executable: str = "pandoc") -> PandocInfo:
    path = shutil.which(executable)
    if not path:
        raise PandocNotFoundError(
            "Pandoc was not found on PATH. Install Pandoc "
            "(https://pandoc.org/installing.html) and ensure a PDF engine "
            "(XeLaTeX recommended via TeX Live / MiKTeX) is available."
        )
    result = subprocess.run(
        [path, "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    first_line = (result.stdout or result.stderr or "").splitlines()
    version = first_line[0] if first_line else "unknown"
    return PandocInfo(path=path, version=version)


def run_pandoc(args: list[str], *, timeout: int | None = None) -> None:
    """Run pandoc; raise PandocError on non-zero exit."""
    logger.debug("Running: %s", " ".join(args))
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise PandocError(
            f"Pandoc failed (exit {completed.returncode}): {stderr[:2000]}",
            returncode=completed.returncode,
            stderr=stderr,
        )
