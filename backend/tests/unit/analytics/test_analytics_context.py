"""Unit tests for analytics context and date filter helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter, DateRangePreset, GroupBy
from app.analytics.utils.date_filters import (
    context_for_day,
    context_for_last_n_days,
    context_from_filter,
    default_dashboard_context,
    utc_end_of_day,
    utc_start_of_day,
)


def test_analytics_context_rejects_inverted_range() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 5, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="start_date must be before or equal to end_date"):
        AnalyticsContext(start_date=start, end_date=end)


def test_context_for_last_n_days_covers_full_calendar_days() -> None:
    end = datetime(2026, 6, 10, 15, 30, tzinfo=UTC)
    context = context_for_last_n_days(3, end=end)

    assert context.start_date == utc_start_of_day(end - timedelta(days=2))
    assert context.end_date == utc_end_of_day(end)


def test_context_for_day_is_single_day_window() -> None:
    moment = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    context = context_for_day(moment)

    assert context.start_date == utc_start_of_day(moment)
    assert context.end_date == utc_end_of_day(moment)


def test_default_dashboard_context_uses_seven_day_window() -> None:
    context = default_dashboard_context()
    span_days = (context.end_date.date() - context.start_date.date()).days + 1

    assert span_days == 7


def test_context_from_filter_uses_explicit_range() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 7, tzinfo=UTC)
    filters = AnalyticsFilter(
        start_date=start,
        end_date=end,
        timezone="UTC",
        group_by=GroupBy.DAY,
        limit=30,
    )

    context = context_from_filter(filters)

    assert context.start_date == start
    assert context.end_date == end
    assert context.group_by == GroupBy.DAY
    assert context.limit == 30


def test_context_from_filter_defaults_to_last_n_days() -> None:
    context = context_from_filter(AnalyticsFilter(), default_days=7)

    span_days = (context.end_date.date() - context.start_date.date()).days + 1
    assert span_days == 7


def test_context_from_filter_supports_range_presets() -> None:
    context = context_from_filter(
        AnalyticsFilter(range_preset=DateRangePreset.LAST_30_DAYS),
    )

    span_days = (context.end_date.date() - context.start_date.date()).days + 1
    assert span_days == 30


def test_context_from_filter_requires_both_bounds() -> None:
    with pytest.raises(ValueError, match="Both start_date and end_date"):
        context_from_filter(
            AnalyticsFilter(start_date=datetime(2026, 6, 1, tzinfo=UTC)),
        )
