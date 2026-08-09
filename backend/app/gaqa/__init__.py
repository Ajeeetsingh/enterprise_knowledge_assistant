"""Phase 4D/4E — Grounded Answer Quality Assurance (GAQA).

Deterministic validator that runs after answer generation.
May recommend refusal/partial overrides via ``recommended_final_answer``;
does not call LLMs or invent information.
"""

from app.gaqa.types import GaqaReport
from app.gaqa.validator import run_gaqa

__all__ = ["GaqaReport", "run_gaqa"]
