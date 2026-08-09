"""Basic metadata analyzer."""

from __future__ import annotations

from pathlib import Path

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.text_utils import detect_language, estimate_page_count
from app.knowledge_engine.types import BasicMetadata


class MetadataAnalyzer:
    name = "metadata"

    def analyze(self, context: AnalyzerContext) -> None:
        request = context.request
        extension = Path(request.filename).suffix.lower().lstrip(".")
        language, _language_confidence = detect_language(request.text)
        page_count = estimate_page_count(request.text) if request.text.strip() else None

        context.knowledge.metadata = BasicMetadata(
            filename=request.filename,
            extension=extension,
            page_count=page_count,
            language=language,
            uploader=request.uploader,
            upload_date=request.upload_date,
            owner=request.owner or request.uploader,
            file_size=request.file_size,
        )
        context.knowledge.language = language
