"""Assign Knowledge Objects to enterprise collections."""

from __future__ import annotations

from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_registry.enums import CollectionSlug

_DEPARTMENT_TO_COLLECTION: dict[str, CollectionSlug] = {
    "hr": CollectionSlug.HR,
    "finance": CollectionSlug.FINANCE,
    "engineering": CollectionSlug.ENGINEERING,
    "it": CollectionSlug.IT,
    "security": CollectionSlug.SECURITY,
    "legal": CollectionSlug.LEGAL,
    "marketing": CollectionSlug.MARKETING,
    "sales": CollectionSlug.SALES,
    "operations": CollectionSlug.OPERATIONS,
    "personal": CollectionSlug.PERSONAL,
    "external": CollectionSlug.EXTERNAL,
    "support": CollectionSlug.SUPPORT,
    "admin": CollectionSlug.ADMIN,
}

_TYPE_HINTS: dict[str, CollectionSlug] = {
    "research paper": CollectionSlug.RESEARCH,
    "financial report": CollectionSlug.FINANCE,
    "invoice": CollectionSlug.FINANCE,
    "contract": CollectionSlug.LEGAL,
    "resume": CollectionSlug.PERSONAL,
}


class CollectionAssigner:
    """Map a Knowledge Object onto one or more collection slugs."""

    def assign(self, knowledge: DocumentKnowledge) -> list[str]:
        selected: list[CollectionSlug] = []
        for department in knowledge.departments:
            mapped = _DEPARTMENT_TO_COLLECTION.get(department.strip().lower())
            if mapped and mapped not in selected:
                selected.append(mapped)

        type_key = knowledge.document_type.strip().lower()
        hinted = _TYPE_HINTS.get(type_key)
        if hinted and hinted not in selected:
            selected.append(hinted)

        filename = knowledge.metadata.filename.lower()
        if "research" in filename and CollectionSlug.RESEARCH not in selected:
            selected.append(CollectionSlug.RESEARCH)

        if not selected:
            selected = [CollectionSlug.UNKNOWN]
        return [item.value for item in selected[:4]]
