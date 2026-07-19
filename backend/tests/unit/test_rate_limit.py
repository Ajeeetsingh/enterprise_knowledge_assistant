"""Unit tests for the in-memory rate limiter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter, enforce_rate_limit, rate_limiter


def test_allows_calls_under_the_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("k", max_calls=2, window_seconds=60) is True
    assert limiter.is_allowed("k", max_calls=2, window_seconds=60) is True


def test_blocks_calls_over_the_limit() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("k", max_calls=1, window_seconds=60) is True
    assert limiter.is_allowed("k", max_calls=1, window_seconds=60) is False


def test_keys_are_isolated() -> None:
    limiter = InMemoryRateLimiter()

    assert limiter.is_allowed("a", max_calls=1, window_seconds=60) is True
    assert limiter.is_allowed("b", max_calls=1, window_seconds=60) is True
    assert limiter.is_allowed("a", max_calls=1, window_seconds=60) is False


def test_enforce_rate_limit_raises_429(monkeypatch: pytest.MonkeyPatch) -> None:
    rate_limiter._events.clear()
    monkeypatch.setattr(
        "app.core.rate_limit.client_ip",
        lambda _request: "203.0.113.10",
    )
    request = MagicMock()

    enforce_rate_limit(request, bucket="test", max_calls=1, window_seconds=60)
    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(request, bucket="test", max_calls=1, window_seconds=60)

    assert exc_info.value.status_code == 429
    rate_limiter._events.clear()
