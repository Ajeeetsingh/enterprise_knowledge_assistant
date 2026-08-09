"""Document type classification analyzer."""

from __future__ import annotations

import re
from pathlib import Path

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.enums import DocumentType

_TYPE_RULES: list[tuple[DocumentType, tuple[str, ...], float]] = [
    (DocumentType.HANDBOOK, ("handbook", "employee handbook", "staff handbook"), 0.95),
    (DocumentType.POLICY, ("policy", "policies", "policy manual", "code of conduct"), 0.9),
    (DocumentType.FINANCIAL_REPORT, ("financial report", "quarterly report", "revenue", "budget", "expense report"), 0.88),
    (DocumentType.CONTRACT, ("contract", "agreement", "terms and conditions", "msa", "nda"), 0.9),
    (DocumentType.INVOICE, ("invoice", "billing statement", "amount due"), 0.92),
    (DocumentType.RESUME, ("resume", "curriculum vitae", "cv ", "work experience"), 0.9),
    (DocumentType.RESEARCH_PAPER, ("abstract", "references", "methodology", "literature review"), 0.8),
    (DocumentType.PRESENTATION, ("slide", "agenda", "deck", "presentation"), 0.75),
    (DocumentType.MANUAL, ("manual", "runbook", "playbook", "how to", "procedure"), 0.85),
]

_FILENAME_HINTS: list[tuple[DocumentType, tuple[str, ...]]] = [
    (DocumentType.HANDBOOK, ("handbook",)),
    (DocumentType.POLICY, ("policy", "policies")),
    (DocumentType.FINANCIAL_REPORT, ("finance", "budget", "revenue", "expense", "quarterly")),
    (DocumentType.CONTRACT, ("contract", "agreement", "nda")),
    (DocumentType.INVOICE, ("invoice",)),
    (DocumentType.RESUME, ("resume", "cv")),
    (DocumentType.MANUAL, ("manual", "runbook", "incident_response")),
]


class DocumentTypeAnalyzer:
    name = "document_type"

    def analyze(self, context: AnalyzerContext) -> None:
        filename = context.request.filename.lower()
        stem = Path(filename).stem.lower()
        haystack = f"{stem}\n{context.request.text[:8000].lower()}"

        best_type = DocumentType.UNKNOWN
        best_score = 0.35
        filename_locked = False

        for doc_type, hints in _FILENAME_HINTS:
            # Prefer exact/strong filename signals over generic body keywords
            # (e.g. incident_response.txt may mention "policy" but is a Manual).
            if any(hint == stem or stem.endswith(f"_{hint}") or stem.startswith(f"{hint}_") for hint in hints):
                best_type = doc_type
                best_score = 0.94
                filename_locked = True
                break
            if any(hint in stem for hint in hints):
                best_type = doc_type
                best_score = 0.9
                filename_locked = True
                break

        if not filename_locked:
            for doc_type, phrases, score in _TYPE_RULES:
                hits = sum(1 for phrase in phrases if phrase in haystack)
                if hits == 0:
                    continue
                weighted = min(0.98, score + 0.03 * (hits - 1))
                if weighted > best_score:
                    best_type = doc_type
                    best_score = weighted

        # Security incident docs are often manuals/playbooks.
        if best_type == DocumentType.UNKNOWN and re.search(
            r"incident|response|playbook", haystack
        ):
            best_type = DocumentType.MANUAL
            best_score = 0.7

        context.knowledge.document_type = best_type.value
        context.knowledge.confidence.document_type = round(best_score, 3)
