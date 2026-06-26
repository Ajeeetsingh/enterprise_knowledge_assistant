"""Unit tests for MetricsService (Phase 7.7)."""

from __future__ import annotations

from unittest.mock import patch

from app.services.metrics_service import MetricsService


@patch("app.services.metrics_service.check_database_connection", return_value=True)
@patch("app.services.metrics_service.get_settings")
@patch("app.services.metrics_service.time.time", return_value=1065.0)
@patch("app.services.metrics_service._APP_STARTED_AT", 1000.0)
def test_get_metrics_returns_runtime_snapshot(
    mock_time,
    mock_get_settings,
    mock_check_db,
) -> None:
    mock_get_settings.return_value.app_version = "0.1.0"

    metrics = MetricsService().get_metrics()

    assert metrics.uptime_seconds == 65
    assert metrics.database_connected is True
    assert metrics.version == "0.1.0"
    mock_check_db.assert_called_once()


@patch("app.services.metrics_service.check_database_connection", return_value=False)
@patch("app.services.metrics_service.get_settings")
@patch("app.services.metrics_service._APP_STARTED_AT", 1000.0)
def test_get_metrics_reports_database_unavailable(
    mock_get_settings,
    mock_check_db,
) -> None:
    mock_get_settings.return_value.app_version = "0.1.0"

    metrics = MetricsService().get_metrics()

    assert metrics.database_connected is False
