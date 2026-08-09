"""Phase 4F — Multi-document synthesis & intelligent answer composition.

Deterministic planner that runs after Evidence Prioritization (4C) and before
prompt generation. Does not retrieve, rewrite evidence, or call an LLM.
"""

from app.answer_synthesis.planner import plan_answer_synthesis
from app.answer_synthesis.types import SynthesisPlan, SynthesisSection

__all__ = ["SynthesisPlan", "SynthesisSection", "plan_answer_synthesis"]
