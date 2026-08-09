"""GAQA report types — validation + reliability diagnostics (Phases 4D/4E)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConceptCoverageItem:
    concept: str
    present_in_answer: bool
    present_in_evidence: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "present_in_answer": self.present_in_answer,
            "present_in_evidence": self.present_in_evidence,
            "status": "covered" if self.present_in_answer else "missing",
        }


@dataclass(frozen=True)
class BlueprintSectionItem:
    section: str
    present: bool

    def to_dict(self) -> dict[str, Any]:
        return {"section": self.section, "present": self.present}


@dataclass(frozen=True)
class EvidenceMappingItem:
    label: str
    source: str
    chunk_ids: tuple[str, ...]
    mentioned_in_answer: bool
    support: str  # supported | partially_supported | unsupported

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "source": self.source,
            "chunk_ids": list(self.chunk_ids),
            "mentioned_in_answer": self.mentioned_in_answer,
            "support": self.support,
        }


@dataclass(frozen=True)
class ClaimSupportItem:
    excerpt: str
    support: str  # supported | partially_supported | unsupported
    overlap_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "excerpt": self.excerpt,
            "support": self.support,
            "overlap_ratio": round(self.overlap_ratio, 4),
        }


@dataclass
class GaqaReport:
    """Deterministic grounded-answer quality assurance report."""

    question_coverage: list[ConceptCoverageItem] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    blueprint_sections: list[BlueprintSectionItem] = field(default_factory=list)
    blueprint_compliance: float = 0.0
    evidence_mappings: list[EvidenceMappingItem] = field(default_factory=list)
    claim_support: list[ClaimSupportItem] = field(default_factory=list)
    unsupported_claim_count: int = 0
    redundant_concepts: list[str] = field(default_factory=list)
    ordering_ok: bool = True
    ordering_notes: list[str] = field(default_factory=list)
    component_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    confidence_label: str = "low"  # high | medium | low
    overall_confidence: float = 0.0
    decisions: list[str] = field(default_factory=list)
    # Phase 4E — reliability diagnostics
    intent_coverage: float = 1.0
    evidence_specificity: float = 1.0
    question_match: float = 1.0
    answer_completeness: str = "complete"
    refusal_reason: str | None = None
    overall_reliability_score: float = 1.0
    reliability_notes: list[str] = field(default_factory=list)
    recommended_final_answer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_coverage": [item.to_dict() for item in self.question_coverage],
            "missing_concepts": list(self.missing_concepts),
            "blueprint_validation": {
                "compliance": round(self.blueprint_compliance, 4),
                "sections": [item.to_dict() for item in self.blueprint_sections],
            },
            "evidence_mapping": [item.to_dict() for item in self.evidence_mappings],
            "claim_support": [item.to_dict() for item in self.claim_support],
            "unsupported_claim_count": self.unsupported_claim_count,
            "redundant_concepts": list(self.redundant_concepts),
            "ordering": {
                "ok": self.ordering_ok,
                "notes": list(self.ordering_notes),
            },
            "confidence_breakdown": {
                "label": self.confidence_label,
                "overall_confidence": round(self.overall_confidence, 4),
                "components": {
                    key: round(value, 4) for key, value in self.component_scores.items()
                },
            },
            "quality_score": {
                "coverage": round(self.component_scores.get("question_coverage", 0.0), 4),
                "grounding": round(self.component_scores.get("grounding", 0.0), 4),
                "blueprint": round(
                    self.component_scores.get("blueprint_compliance", 0.0), 4
                ),
                "redundancy": round(
                    self.component_scores.get("redundancy_penalty", 0.0), 4
                ),
                "unsupported_claims": round(
                    self.component_scores.get("unsupported_rate", 0.0), 4
                ),
                "overall": round(self.overall_score, 4),
            },
            "intent_coverage": round(self.intent_coverage, 4),
            "evidence_specificity": round(self.evidence_specificity, 4),
            "question_match": round(self.question_match, 4),
            "answer_completeness": self.answer_completeness,
            "refusal_reason": self.refusal_reason,
            "overall_reliability_score": round(self.overall_reliability_score, 4),
            "reliability_notes": list(self.reliability_notes),
            "recommended_final_answer": self.recommended_final_answer,
            "decisions": list(self.decisions),
        }
