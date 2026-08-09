"""Response Experience Engine entrypoint (Phase 5A).

Plans presentation layout after answer generation. Does not alter answer text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.response_experience.selector import build_response_layout
from app.response_experience.types import ResponseLayout

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.answer_synthesis.types import SynthesisPlan
    from app.evidence_organization.types import EvidenceGraph


def plan_response_experience(
    *,
    question: str,
    answer: str | None = None,
    answer_plan: AnswerPlan | None = None,
    evidence_graph: EvidenceGraph | None = None,
    answer_synthesis: SynthesisPlan | None = None,
    extra_context: dict[str, Any] | None = None,
) -> ResponseLayout:
    """Return a deterministic ResponseLayout for Phase 5B rendering."""
    return build_response_layout(
        question=question,
        answer=answer,
        answer_plan=answer_plan,
        evidence_graph=evidence_graph,
        answer_synthesis=answer_synthesis,
        extra_context=extra_context,
    )
