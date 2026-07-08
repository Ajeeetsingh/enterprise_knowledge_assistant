"""Unit tests for analytics report payload helpers (Phase 11.7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.analytics.schemas.common import ChartSeries
from app.analytics.services.report_payload import (
    chart_series_to_trend,
    dict_to_table,
    items_to_table,
    snapshot_to_kpis,
)


@dataclass(frozen=True)
class _SampleSnapshot:
    total_users: int
    active_user_percentage: float
    start_date: datetime
    end_date: datetime


class TestReportPayloadHelpers:
    def test_snapshot_to_kpis_skips_date_fields(self) -> None:
        snapshot = _SampleSnapshot(
            total_users=10,
            active_user_percentage=42.5,
            start_date=datetime(2026, 6, 1, tzinfo=UTC),
            end_date=datetime(2026, 6, 7, tzinfo=UTC),
        )

        kpis = snapshot_to_kpis(snapshot)

        assert ("Total Users", "10") in kpis
        assert ("Active User Percentage", "42.50") in kpis
        assert all("Start Date" not in label for label, _ in kpis)

    def test_dict_to_table_sorts_rows(self) -> None:
        table = dict_to_table("Distribution", {"beta": 2, "alpha": 1})

        assert table.headers == ("Key", "Value")
        assert table.rows[0] == ("alpha", "1")

    def test_items_to_table_uses_requested_columns(self) -> None:
        table = items_to_table(
            "Top Questions",
            [{"question": "What is RAG?", "count": 3}],
            column_order=("question", "count"),
        )

        assert table.rows == (("What is RAG?", "3"),)

    def test_chart_series_to_trend_copies_points(self) -> None:
        series = ChartSeries(event_type="questions", points={"2026-06-01": 4})
        trend = chart_series_to_trend("Questions", series)

        assert trend.name == "Questions"
        assert trend.points == {"2026-06-01": 4}
