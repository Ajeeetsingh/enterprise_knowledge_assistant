"""Public guest/demo chat endpoint (no authentication, no RAG)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.rate_limit import enforce_rate_limit
from app.schemas.demo import GuestAskRequest, GuestAskResponse
from app.services.guest_demo_service import GuestDemoService

router = APIRouter()

# Stricter than authenticated chat (30/min) — portfolio demo abuse reduction.
GUEST_ASK_RATE_LIMIT = 20
GUEST_ASK_RATE_WINDOW_SECONDS = 60


@router.post(
    "/ask",
    response_model=GuestAskResponse,
    summary="Ask a guest demo question",
    description=(
        "Public demo endpoint. Supports product-help, general knowledge, and "
        "safety boundaries only. Never retrieves organisational documents."
    ),
)
def guest_ask(body: GuestAskRequest, request: Request) -> GuestAskResponse:
    """Answer a guest question without authentication or document access."""
    enforce_rate_limit(
        request,
        bucket="guest-ask",
        max_calls=GUEST_ASK_RATE_LIMIT,
        window_seconds=GUEST_ASK_RATE_WINDOW_SECONDS,
        detail="Too many demo questions. Please try again later.",
    )
    return GuestDemoService().ask(body)
