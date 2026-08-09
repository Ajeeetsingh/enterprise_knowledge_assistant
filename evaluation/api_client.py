"""HTTP client that mirrors the Knowra frontend chat request flow.

Frontend flow:
1. ``POST /conversations`` with ``{"title": null}`` (or a title)
2. ``POST /chat/ask`` with ``{"conversation_id": "<uuid>", "question": "..."}``
3. Bearer token via ``Authorization`` header
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from config import Settings
from logger import EvaluationLogger


@dataclass
class ApiCallResult:
    """Normalized result of a single HTTP call."""

    ok: bool
    http_status: int | None
    payload: dict[str, Any] | None
    error: str | None
    raw_body: str | None = None


class KnowraApiClient:
    """Thin client for login, conversation create, and chat ask."""

    def __init__(self, settings: Settings, logger: EvaluationLogger) -> None:
        self.settings = settings
        self.logger = logger
        self._access_token: str | None = settings.access_token

    def ensure_authenticated(self) -> None:
        """Use configured token or login with email/password."""
        if self._access_token:
            self.logger.debug("Using KNOWRA_ACCESS_TOKEN from configuration.")
            return

        if not self.settings.email or not self.settings.password:
            raise RuntimeError(
                "Authentication required. Set KNOWRA_ACCESS_TOKEN, or both "
                "KNOWRA_EMAIL and KNOWRA_PASSWORD in evaluation/.env."
            )

        self.logger.info(f"Logging in as {self.settings.email}")
        result = self._request_json(
            method="POST",
            url=self.settings.login_url,
            payload={
                "email": self.settings.email,
                "password": self.settings.password,
            },
            authenticated=False,
        )
        if not result.ok or not result.payload:
            raise RuntimeError(
                f"Login failed (HTTP {result.http_status}): {result.error}"
            )

        token = result.payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("Login response did not include access_token.")
        self._access_token = token.strip()
        self.logger.info("Login succeeded.")

    def create_conversation(self, title: str | None = None) -> str:
        """Create a conversation (same contract as the frontend)."""
        result = self._request_json(
            method="POST",
            url=self.settings.conversations_url,
            payload={"title": title},
            authenticated=True,
        )
        if not result.ok or not result.payload:
            raise RuntimeError(
                f"Failed to create conversation (HTTP {result.http_status}): "
                f"{result.error}"
            )
        conversation_id = result.payload.get("id")
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            raise RuntimeError("Conversation create response missing id.")
        return conversation_id.strip()

    def ask_question(self, conversation_id: str, question: str) -> ApiCallResult:
        """
        Call ``POST /chat/ask`` with the frontend request body:

        ``{"conversation_id": "...", "question": "..."}``
        """
        return self._request_json(
            method="POST",
            url=self.settings.chat_ask_url,
            payload={
                "conversation_id": conversation_id,
                "question": question,
            },
            authenticated=True,
        )

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        authenticated: bool,
    ) -> ApiCallResult:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.settings.user_agent,
        }
        if authenticated:
            if not self._access_token:
                return ApiCallResult(
                    ok=False,
                    http_status=None,
                    payload=None,
                    error="Missing access token before authenticated request.",
                )
            headers["Authorization"] = f"Bearer {self._access_token}"

        body_bytes: bytes | None = None
        if payload is not None:
            body_bytes = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.settings.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = int(getattr(response, "status", 200) or 200)
                parsed = self._safe_json(raw)
                return ApiCallResult(
                    ok=200 <= status < 300,
                    http_status=status,
                    payload=parsed if isinstance(parsed, dict) else None,
                    error=None if 200 <= status < 300 else f"Unexpected status {status}",
                    raw_body=raw,
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            parsed = self._safe_json(raw)
            detail = None
            if isinstance(parsed, dict):
                detail = parsed.get("detail") or parsed.get("message")
            error_text = str(detail) if detail else (raw[:500] or str(exc))
            self.logger.debug(
                f"HTTPError {exc.code} for {method} {url}: {error_text}"
            )
            return ApiCallResult(
                ok=False,
                http_status=int(exc.code),
                payload=parsed if isinstance(parsed, dict) else None,
                error=error_text,
                raw_body=raw,
            )
        except urllib.error.URLError as exc:
            self.logger.exception(f"Network error for {method} {url}", exc)
            return ApiCallResult(
                ok=False,
                http_status=None,
                payload=None,
                error=f"Network error: {exc.reason}",
            )
        except TimeoutError as exc:
            self.logger.exception(f"Timeout for {method} {url}", exc)
            return ApiCallResult(
                ok=False,
                http_status=None,
                payload=None,
                error=f"Request timed out after {self.settings.timeout_seconds}s",
            )
        except Exception as exc:  # noqa: BLE001 — keep evaluation running
            self.logger.exception(f"Unexpected error for {method} {url}", exc)
            return ApiCallResult(
                ok=False,
                http_status=None,
                payload=None,
                error=f"{type(exc).__name__}: {exc}",
            )

    @staticmethod
    def _safe_json(raw: str) -> Any:
        if not raw or not raw.strip():
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
