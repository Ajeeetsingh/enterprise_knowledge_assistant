"""Shared helpers for extracting information from incoming HTTP requests."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str | None:
    """Extract the client IP from *request*, honouring forwarded headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
