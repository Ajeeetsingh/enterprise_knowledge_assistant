"""UTC date-range helpers for analytics queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter, DateRangePreset, GroupBy


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


def utc_start_of_day(value: datetime | None = None) -> datetime:
    """Return midnight UTC for the given calendar day (default: today)."""
    moment = value.astimezone(UTC) if value is not None else utc_now()
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def utc_end_of_day(value: datetime | None = None) -> datetime:
    """Return 23:59:59.999999 UTC for the given calendar day (default: today)."""
    start = utc_start_of_day(value)
    return start + timedelta(days=1) - timedelta(microseconds=1)


def utc_start_of_week(value: datetime | None = None) -> datetime:
    """Return Monday 00:00 UTC for the week containing *value*."""
    start_of_day = utc_start_of_day(value)
    return start_of_day - timedelta(days=start_of_day.weekday())


def utc_start_of_month(value: datetime | None = None) -> datetime:
    """Return the first day 00:00 UTC for the month containing *value*."""
    moment = value.astimezone(UTC) if value is not None else utc_now()
    return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def context_for_last_n_days(
    days: int,
    *,
    end: datetime | None = None,
    timezone: str = "UTC",
    group_by: GroupBy | None = None,
    limit: int | None = None,
) -> AnalyticsContext:
    """Return a context covering the last *days* full UTC calendar days."""
    if days < 1:
        raise ValueError("days must be at least 1.")
    end_moment = utc_end_of_day(end)
    start_moment = utc_start_of_day(end_moment - timedelta(days=days - 1))
    return AnalyticsContext(
        start_date=start_moment,
        end_date=end_moment,
        timezone=timezone,
        group_by=group_by.value if group_by is not None else None,
        limit=limit,
    )


def context_for_day(
    value: datetime | None = None,
    *,
    timezone: str = "UTC",
    group_by: GroupBy | None = None,
    limit: int | None = None,
) -> AnalyticsContext:
    """Return a context for a single UTC calendar day."""
    anchor = value if value is not None else utc_now()
    return AnalyticsContext(
        start_date=utc_start_of_day(anchor),
        end_date=utc_end_of_day(anchor),
        timezone=timezone,
        group_by=group_by.value if group_by is not None else None,
        limit=limit,
    )


def default_dashboard_context() -> AnalyticsContext:
    """Return the default seven-day dashboard reporting window."""
    return context_for_last_n_days(7)


def context_from_filter(
    filters: AnalyticsFilter,
    *,
    default_days: int = 7,
) -> AnalyticsContext:
    """Build an ``AnalyticsContext`` from optional API filter parameters."""
    if filters.start_date is not None and filters.end_date is not None:
        return AnalyticsContext(
            start_date=filters.start_date,
            end_date=filters.end_date,
            timezone=filters.timezone,
            group_by=filters.group_by.value if filters.group_by is not None else None,
            limit=filters.limit,
        )
    if filters.start_date is not None or filters.end_date is not None:
        raise ValueError("Both start_date and end_date are required for a custom range.")

    preset_days = _preset_days(filters.range_preset, default_days=default_days)
    return context_for_last_n_days(
        preset_days,
        timezone=filters.timezone,
        group_by=filters.group_by,
        limit=filters.limit,
    )


def _preset_days(
    preset: DateRangePreset | None,
    *,
    default_days: int,
) -> int:
    """Map a date-range preset to a day count."""
    if preset is None:
        return default_days
    if preset == DateRangePreset.TODAY:
        return 1
    if preset == DateRangePreset.LAST_7_DAYS:
        return 7
    if preset == DateRangePreset.LAST_30_DAYS:
        return 30
    if preset == DateRangePreset.LAST_90_DAYS:
        return 90
    if preset == DateRangePreset.CUSTOM:
        raise ValueError("Both start_date and end_date are required for a custom range.")
    return default_days
