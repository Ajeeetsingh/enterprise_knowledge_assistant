"""Pure aggregation helpers for analytics services."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any


def sum_values(values: Iterable[float | int]) -> float:
    """Return the numeric sum of *values*."""
    return float(sum(values))


def average(values: Sequence[float | int]) -> float | None:
    """Return the arithmetic mean or ``None`` when *values* is empty."""
    if not values:
        return None
    return sum_values(values) / len(values)


def bucket_counts_by_day(
    timestamps: Iterable[datetime],
) -> dict[str, int]:
    """Count occurrences grouped by UTC calendar day (``YYYY-MM-DD`` keys)."""
    counter: Counter[str] = Counter()
    for timestamp in timestamps:
        day = timestamp.astimezone(UTC).date().isoformat()
        counter[day] += 1
    return dict(sorted(counter.items()))


def extract_metadata_values(
    metadata_rows: Iterable[Mapping[str, Any] | None],
    key: str,
) -> list[float]:
    """Collect numeric metadata values for *key*, skipping invalid rows."""
    values: list[float] = []
    for metadata in metadata_rows:
        if not metadata or key not in metadata:
            continue
        raw = metadata[key]
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            values.append(float(raw))
    return values
