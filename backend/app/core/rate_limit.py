"""Lightweight in-memory rate limiting for public-facing endpoints.

No external dependencies — suitable for a single-process portfolio/demo
deployment. For multi-worker production, prefer a shared store or reverse-
proxy limits (nginx ``limit_req``, Cloudflare, etc.).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.request_utils import client_ip


class InMemoryRateLimiter:
    """Sliding-window rate limiter keyed by arbitrary strings."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str, *, max_calls: int, window_seconds: float) -> bool:
        """Return True and record the call when under the limit."""
        now = time.monotonic()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= max_calls:
                return False
            bucket.append(now)
            return True


# Process-wide limiter shared by request handlers.
rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    max_calls: int,
    window_seconds: float,
    detail: str = "Too many requests. Please try again later.",
) -> None:
    """Raise HTTP 429 when the caller exceeds the configured budget."""
    ip = client_ip(request) or "unknown"
    key = f"{bucket}:{ip}"
    if not rate_limiter.is_allowed(
        key, max_calls=max_calls, window_seconds=window_seconds
    ):
        raise HTTPException(status_code=429, detail=detail)
