"""Phase 4B — Evidence Organization.

Reorganizes retrieved chunks into an Evidence Graph for prompting.
Does not invent, summarize, rewrite, or change retrieval.
"""

from app.evidence_organization.enums import EvidenceRelationKind, EvidenceStructureKind
from app.evidence_organization.organizer import organize_evidence
from app.evidence_organization.types import EvidenceGraph, EvidenceLink, EvidenceNode

__all__ = [
    "EvidenceGraph",
    "EvidenceLink",
    "EvidenceNode",
    "EvidenceRelationKind",
    "EvidenceStructureKind",
    "organize_evidence",
]
