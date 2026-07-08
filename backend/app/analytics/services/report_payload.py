"""Normalized report payload structures for analytics exporters (Phase 11.7)."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from typing import Any

from app.analytics.schemas.common import ChartSeries


@dataclass(frozen=True)
class ReportTableSection:
    """Tabular section included in exported reports."""

    name: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ReportTrendSection:
    """Time-series section included in exported reports."""

    name: str
    points: dict[str, int | float]


@dataclass(frozen=True)
class AnalyticsReportPayload:
    """Unified analytics report consumed by CSV, Excel, and PDF exporters."""

    module: str
    module_title: str
    generated_at: datetime
    start_date: datetime
    end_date: datetime
    kpis: tuple[tuple[str, str], ...]
    tables: tuple[ReportTableSection, ...]
    trends: tuple[ReportTrendSection, ...]


def humanize_key(key: str) -> str:
    """Convert snake_case keys into report labels."""
    return key.replace("_", " ").strip().title()


def format_report_value(value: Any) -> str:
    """Render a snapshot value for export."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def snapshot_to_kpis(snapshot: object) -> tuple[tuple[str, str], ...]:
    """Convert a dataclass snapshot into KPI rows."""
    skip = {"start_date", "end_date"}
    rows: list[tuple[str, str]] = []
    if is_dataclass(snapshot):
        for field in fields(snapshot):
            if field.name in skip:
                continue
            rows.append(
                (humanize_key(field.name), format_report_value(getattr(snapshot, field.name))),
            )
    return tuple(rows)


def chart_series_to_trend(name: str, series: ChartSeries) -> ReportTrendSection:
    """Convert a chart series into a trend section."""
    return ReportTrendSection(name=name, points=dict(series.points))


def dict_to_table(name: str, distribution: dict[str, int | float]) -> ReportTableSection:
    """Convert a mapping into a two-column table."""
    rows = tuple(
        (key, format_report_value(value))
        for key, value in sorted(distribution.items(), key=lambda item: item[0])
    )
    return ReportTableSection(name=name, headers=("Key", "Value"), rows=rows)


def items_to_table(
    name: str,
    items: list[dict[str, object]],
    *,
    column_order: tuple[str, ...] | None = None,
) -> ReportTableSection:
    """Convert list-of-dict rows into a table section."""
    if not items:
        headers: tuple[str, ...] = column_order or ()
        return ReportTableSection(name=name, headers=headers, rows=())

    if column_order is None:
        keys: list[str] = []
        for item in items:
            for key in item:
                if key not in keys:
                    keys.append(key)
        column_order = tuple(keys)

    headers = tuple(humanize_key(column) for column in column_order)
    rows = tuple(
        tuple(format_report_value(item.get(column)) for column in column_order)
        for item in items
    )
    return ReportTableSection(name=name, headers=headers, rows=rows)


def dataclass_rows_to_table(
    name: str,
    rows: list[object],
    *,
    column_order: tuple[str, ...] | None = None,
) -> ReportTableSection:
    """Convert dataclass rows into a table section."""
    dict_rows = [
        {field.name: getattr(row, field.name) for field in fields(row)}
        for row in rows
        if is_dataclass(row)
    ]
    return items_to_table(name, dict_rows, column_order=column_order)
