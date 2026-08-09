"""Answer planner — selects structure only; never invents facts."""

from __future__ import annotations

from app.answer_planning.blueprints import get_blueprint
from app.answer_planning.classifier import classify_answer_type
from app.answer_planning.types import AnswerPlan


def plan_answer(question: str) -> AnswerPlan:
    """Build a deterministic answer plan for the question.

    Does not inspect retrieved chunks and does not generate answer content.
    Retrieved evidence remains the sole factual source in the prompt layer.
    """
    decision = classify_answer_type(question)
    blueprint = get_blueprint(decision.answer_type)
    return AnswerPlan(
        answer_type=decision.answer_type,
        blueprint=blueprint,
        reason=decision.reason,
        matched_signals=decision.matched_signals,
    )
