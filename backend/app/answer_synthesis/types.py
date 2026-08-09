"""Types for Phase 4F answer synthesis planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SynthesisSection:
    """One concept-oriented answer section backed by retrieved evidence."""

    concept: str
    sources: list[str] = field(default_factory=list)
    evidence_texts: list[str] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    owner_role: str = "supporting"  # primary | supporting | context
    contribution_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "sources": list(self.sources),
            "owner_role": self.owner_role,
            "chunk_ids": list(self.chunk_ids),
            "contribution_chars": self.contribution_chars,
            "evidence_preview": [
                (text[:200] + "…") if len(text) > 200 else text
                for text in self.evidence_texts[:2]
            ],
        }


@dataclass
class SynthesisPlan:
    """Deterministic multi-document synthesis plan (pre-prompt, no generation)."""

    primary_document: str | None = None
    supporting_documents: list[str] = field(default_factory=list)
    context_documents: list[str] = field(default_factory=list)
    sections: list[SynthesisSection] = field(default_factory=list)
    concept_flow: list[str] = field(default_factory=list)
    concept_coverage: list[str] = field(default_factory=list)
    dropped_concepts: list[str] = field(default_factory=list)
    unsupported_concepts: list[str] = field(default_factory=list)
    document_contribution: dict[str, float] = field(default_factory=dict)
    mode: str = "single_document"  # single_document | multi_document | executive | unsupported
    is_unsupported: bool = False
    refusal_message: str | None = None
    decisions: list[str] = field(default_factory=list)
    answer_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "answer_type": self.answer_type,
            "primary_document": self.primary_document,
            "supporting_documents": list(self.supporting_documents),
            "context_documents": list(self.context_documents),
            "concept_flow": list(self.concept_flow),
            "concept_coverage": list(self.concept_coverage),
            "dropped_concepts": list(self.dropped_concepts),
            "unsupported_concepts": list(self.unsupported_concepts),
            "document_contribution_pct": {
                key: round(value, 2) for key, value in self.document_contribution.items()
            },
            "section_ownership": [
                {
                    "concept": section.concept,
                    "sources": list(section.sources),
                    "owner_role": section.owner_role,
                }
                for section in self.sections
            ],
            "sections": [section.to_dict() for section in self.sections],
            "is_unsupported": self.is_unsupported,
            "refusal_message": self.refusal_message,
            "decisions": list(self.decisions),
        }

    def format_for_prompt(self) -> str:
        """Render concept-oriented evidence without retrieval artifacts."""
        if self.is_unsupported and self.refusal_message:
            return (
                "Synthesis guidance:\n"
                "The retrieved evidence does not contain the requested fact.\n"
                f"Respond with exactly this message:\n{self.refusal_message}"
            )

        if not self.sections:
            return (
                "Knowledge evidence for synthesis:\n"
                "(No document excerpts available.)"
            )

        lines: list[str] = [
            "Knowledge evidence for synthesis "
            "(write one coherent answer from these facts only):",
        ]
        if self.primary_document:
            lines.append(f"Primary source to prefer: {self.primary_document}")
        if self.supporting_documents:
            lines.append(
                "Supporting sources (enrich, do not replace primary): "
                + ", ".join(self.supporting_documents)
            )
        if self.concept_flow:
            lines.append("Concept flow: " + " → ".join(self.concept_flow))

        if self.mode in {"multi_document", "executive"}:
            lines.append(
                "Organize the answer by the concept sections below — "
                "not by document boundaries. Produce one continuous explanation. "
                "Cite sources naturally inside the prose when helpful. "
                "Do not mention internal labels, scores, chunk ids, or ranking terms."
            )
        else:
            lines.append(
                "Answer from the evidence below in clear prose. "
                "Do not mention internal labels, scores, chunk ids, or ranking terms."
            )
        lines.append("")

        for section in self.sections:
            lines.append(f"## {section.concept}")
            if section.sources:
                if len(section.sources) == 1:
                    lines.append(f"Source: {section.sources[0]}")
                else:
                    lines.append("Sources: " + ", ".join(section.sources))
            for text in section.evidence_texts:
                cleaned = text.strip()
                if not cleaned:
                    continue
                lines.append("---")
                lines.append(cleaned)
                lines.append("---")
            lines.append("")

        lines.append(
            "Every factual claim must come from the evidence above. "
            "If a concept section has no relevant facts for the question, omit it. "
            "Do not invent facts to fill gaps."
        )
        return "\n".join(lines)
