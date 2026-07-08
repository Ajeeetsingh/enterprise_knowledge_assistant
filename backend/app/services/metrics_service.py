"""System-level runtime metrics (Phase 7.7)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import get_settings
from app.db.session import check_database_connection

_APP_STARTED_AT = time.time()


@dataclass(frozen=True)
class SystemMetrics:
    """Lightweight runtime metrics for operational visibility."""

    uptime_seconds: int
    database_connected: bool
    version: str


class MetricsService:
    """Expose process uptime and infrastructure readiness signals."""

    def get_metrics(self) -> SystemMetrics:
        """Return current system-level metrics."""
        settings = get_settings()
        uptime = max(0, int(time.time() - _APP_STARTED_AT))
        return SystemMetrics(
            uptime_seconds=uptime,
            database_connected=check_database_connection(),
            version=settings.app_version,
        )

    def get_runtime_info(self) -> tuple[int, str]:
        """Return process uptime and application version without infrastructure probes."""
        settings = get_settings()
        uptime = max(0, int(time.time() - _APP_STARTED_AT))
        return uptime, settings.app_version


def build_metrics_service() -> MetricsService:
    """Return a stateless metrics service instance."""
    return MetricsService()
