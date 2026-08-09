"""Tag synthesis analyzer."""

from __future__ import annotations

from app.knowledge_engine.analyzers.base import AnalyzerContext


class TagAnalyzer:
    name = "tags"

    def analyze(self, context: AnalyzerContext) -> None:
        knowledge = context.knowledge
        tags: list[str] = []

        if knowledge.document_type and knowledge.document_type != "Unknown":
            tags.append(knowledge.document_type.lower().replace(" ", "-"))

        for department in knowledge.departments:
            if department != "Unknown":
                tags.append(department.lower())

        for topic in knowledge.topics[:5]:
            tags.append(topic.lower().replace(" ", "-"))

        for keyword in knowledge.keywords[:5]:
            tags.append(keyword.lower().replace(" ", "-"))

        if knowledge.language and knowledge.language != "unknown":
            tags.append(f"lang-{knowledge.language}")

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_tags: list[str] = []
        for tag in tags:
            cleaned = tag.strip("-")
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            unique_tags.append(cleaned)

        knowledge.tags = unique_tags[:20]
        knowledge.confidence.tags = 0.75 if unique_tags else 0.2
