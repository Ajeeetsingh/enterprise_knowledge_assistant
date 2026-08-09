"""Validate CandidateEvidenceSet completeness."""

from __future__ import annotations

from app.knowledge_execution.models.types import CandidateEvidenceSet


class EvidenceSetValidator:
    def validate(self, evidence_set: CandidateEvidenceSet) -> list[str]:
        errors: list[str] = []
        if not evidence_set.execution_id:
            errors.append("missing_execution_id")
        if not evidence_set.plan_id:
            errors.append("missing_plan_id")
        if evidence_set.engine_version == "":
            errors.append("missing_engine_version")
        for candidate in evidence_set.candidates:
            if not candidate.explanation:
                errors.append(f"missing_explanation:{candidate.document_id}")
            if not candidate.supporting_indexes:
                errors.append(f"missing_supporting_indexes:{candidate.document_id}")
        if errors:
            evidence_set.status = "invalid"
            evidence_set.diagnostics.failures.extend(errors)
        return errors
