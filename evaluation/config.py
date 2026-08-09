"""Configuration for the standalone Knowra evaluation utility.

Values can be set via environment variables or an ``evaluation/.env`` file.
You should not need to edit this module for normal evaluation runs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from utils import load_env_file, parse_bool, parse_float

# evaluation/ → project root
EVALUATION_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = EVALUATION_DIR.parent
TEST_DOCS_ROOT: Path = PROJECT_ROOT / "docs" / "test_docs"

# Load local env overrides (does not override already-exported process env).
load_env_file(EVALUATION_DIR / ".env")
load_env_file(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime settings for talking to the Knowra chat API."""

    api_base_url: str
    timeout_seconds: float
    access_token: str | None
    email: str | None
    password: str | None
    create_conversation_per_question: bool
    request_delay_seconds: float
    conversation_title_prefix: str
    user_agent: str

    @property
    def chat_ask_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/chat/ask"

    @property
    def conversations_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/conversations"

    @property
    def login_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/auth/login"


def load_settings() -> Settings:
    """Build settings from environment variables."""
    return Settings(
        api_base_url=os.getenv(
            "KNOWRA_API_BASE_URL",
            "http://localhost:8000/api/v1",
        ).strip(),
        timeout_seconds=parse_float(
            os.getenv("KNOWRA_REQUEST_TIMEOUT", "120"),
            default=120.0,
        ),
        access_token=_optional_str(os.getenv("KNOWRA_ACCESS_TOKEN")),
        email=_optional_str(os.getenv("KNOWRA_EMAIL")),
        password=_optional_str(os.getenv("KNOWRA_PASSWORD")),
        create_conversation_per_question=parse_bool(
            os.getenv("KNOWRA_CREATE_CONVERSATION_PER_QUESTION", "true"),
            default=True,
        ),
        request_delay_seconds=parse_float(
            os.getenv("KNOWRA_REQUEST_DELAY_SECONDS", "2.1"),
            default=2.1,
        ),
        conversation_title_prefix=os.getenv(
            "KNOWRA_CONVERSATION_TITLE_PREFIX",
            "Knowra Evaluation",
        ).strip()
        or "Knowra Evaluation",
        user_agent=os.getenv(
            "KNOWRA_USER_AGENT",
            "KnowraEvaluationUtility/1.0",
        ).strip()
        or "KnowraEvaluationUtility/1.0",
    )


def domain_dir(domain_name: str) -> Path:
    """Return ``docs/test_docs/<domain_name>``."""
    return TEST_DOCS_ROOT / domain_name


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
