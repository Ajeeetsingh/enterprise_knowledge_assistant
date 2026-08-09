"""Phase 4C — Evidence Prioritization & Answer Composition.

Operates after Evidence Organizer and before Prompt Builder.
Does not modify retrieval, organization, or answer planning logic.
"""

from app.evidence_composition.composer import compose_answer_evidence
from app.evidence_composition.enums import EvidencePriority
from app.evidence_composition.types import AnswerComposition, PrioritizedEvidence

__all__ = [
    "AnswerComposition",
    "EvidencePriority",
    "PrioritizedEvidence",
    "compose_answer_evidence",
]
