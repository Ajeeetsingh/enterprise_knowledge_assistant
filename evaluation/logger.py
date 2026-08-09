"""File + console logging for evaluation runs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class EvaluationLogger:
    """Append-only logger that overwrites ``logs.txt`` at the start of a run."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("", encoding="utf-8")
        self.info(f"Log started at {self._timestamp()}")

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def debug(self, message: str) -> None:
        self._write("DEBUG", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)
        # Surface failures in the terminal without drowning progress output.
        print(f"  ! {message}")

    def exception(self, message: str, exc: BaseException) -> None:
        self._write("EXCEPTION", f"{message}: {type(exc).__name__}: {exc}")
        print(f"  ! {message}: {type(exc).__name__}: {exc}")

    def _write(self, level: str, message: str) -> None:
        line = f"[{self._timestamp()}] [{level}] {message}\n"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
