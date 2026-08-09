"""Phase 5 — Response Experience presentation layer (5A–5E).

Presentation only. Does not change retrieval, grounding, or answer meaning.
"""

from app.response_experience.engine import plan_response_experience
from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.response_experience.components import (
    enrich_with_adaptive_components,
    requested_components,
)
from app.response_experience.finalize import FinalizeResult, finalize_enterprise_markdown
from app.response_experience.markdown import (
    RenderResult,
    content_preserved,
    render_enterprise_markdown,
)
from app.response_experience.polish import PolishResult, polish_enterprise_markdown
from app.response_experience.types import ResponseLayout

__all__ = [
    "FinalizeResult",
    "PolishResult",
    "RenderResult",
    "ResponseComponent",
    "ResponseLayout",
    "ResponseLayoutType",
    "content_preserved",
    "enrich_with_adaptive_components",
    "finalize_enterprise_markdown",
    "plan_response_experience",
    "polish_enterprise_markdown",
    "render_enterprise_markdown",
    "requested_components",
]
