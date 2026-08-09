"""Phase 4A — Intelligent Answer Planning.

Sits between retrieval and prompt building. Selects answer structure only;
never generates factual content.
"""

from app.answer_planning.enums import AnswerType
from app.answer_planning.planner import plan_answer
from app.answer_planning.types import AnswerBlueprint, AnswerPlan

__all__ = [
    "AnswerBlueprint",
    "AnswerPlan",
    "AnswerType",
    "plan_answer",
]
