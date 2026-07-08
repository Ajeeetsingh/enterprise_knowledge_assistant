"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

from app.config import get_settings


class StructuredFormatter(logging.Formatter):
    """Key-value structured log formatter for production-friendly output."""

    def format(self, record: logging.LogRecord) -> str:
        parts: list[str] = [
            f"timestamp={self.formatTime(record, self.datefmt)}",
            f"level={record.levelname}",
            f"logger={record.name}",
            f"message={record.getMessage()}",
        ]

        extra_fields: dict[str, Any] = getattr(record, "structured_fields", {})
        for key, value in extra_fields.items():
            parts.append(f"{key}={value}")

        if record.exc_info:
            parts.append(f"exception={self.formatException(record.exc_info)}")

        return " ".join(parts)


def setup_logging() -> None:
    """Configure root logger with structured formatting."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
    _configure_third_party_loggers(settings)


def _configure_third_party_loggers(settings) -> None:
    """Reduce noisy HTTP / ML library INFO logs unless debug mode is enabled."""
    noisy_loggers = (
        "httpx",
        "httpcore",
        "huggingface_hub",
        "transformers",
        "urllib3",
        "filelock",
        "sentence_transformers",
    )
    noisy_level = logging.DEBUG if settings.debug else logging.WARNING
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(noisy_level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def log_with_fields(
    logger: logging.Logger,
    level: int,
    message: str,
    **fields: Any,
) -> None:
    """Emit a log record with structured key-value fields."""
    logger.log(level, message, extra={"structured_fields": fields})
