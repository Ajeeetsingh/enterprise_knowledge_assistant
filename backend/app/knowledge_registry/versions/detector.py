"""Document version awareness for the Knowledge Registry."""

from __future__ import annotations

import re
from pathlib import Path

from app.knowledge_engine.types import DocumentKnowledge

_VERSION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)[_\-\s]v(\d+)(?:\b|_)"), "v{n}"),
    (re.compile(r"(?i)\brev(?:ision)?[_\-\s]?(\d+)\b"), "rev{n}"),
    (re.compile(r"(?i)\bversion[_\-\s]?(\d+)\b"), "v{n}"),
    (re.compile(r"(?i)[_\-](\d{1,2})(?:\.[a-z]+)?$"), "v{n}"),
]

_STRIP_SUFFIXES = re.compile(
    r"(?i)([_\-\s]v\d+|_\d{1,2}|[_\-\s]final|[_\-\s]draft|[_\-\s]copy|[_\-\s]rev\d+)$"
)


class VersionDetector:
    """Detect likely version labels and stable version-group keys."""

    def detect(self, knowledge: DocumentKnowledge) -> tuple[str, str | None, int]:
        filename = knowledge.metadata.filename or "document"
        stem = Path(filename).stem
        label, rank = self._label_and_rank(stem)
        group_key = self._group_key(stem, knowledge)
        return group_key, label, rank

    def _label_and_rank(self, stem: str) -> tuple[str | None, int]:
        lowered = stem.lower()
        if "final" in lowered:
            return "final", 90
        if "draft" in lowered:
            return "draft", 10
        for pattern, template in _VERSION_PATTERNS:
            match = pattern.search(stem)
            if not match:
                continue
            number = int(match.group(1))
            return template.format(n=number), number
        return "v1", 1

    def _group_key(self, stem: str, knowledge: DocumentKnowledge) -> str:
        cleaned = stem
        for _ in range(3):
            updated = _STRIP_SUFFIXES.sub("", cleaned)
            if updated == cleaned:
                break
            cleaned = updated
        cleaned = re.sub(r"[_\-\s]+", "_", cleaned).strip("_").lower()
        dept = (knowledge.departments[0] if knowledge.departments else "unknown").lower()
        doc_type = knowledge.document_type.lower().replace(" ", "_")
        return f"{dept}:{doc_type}:{cleaned}"
