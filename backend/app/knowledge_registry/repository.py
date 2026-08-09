"""Persistence for Knowledge Registry entries."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.db.models.knowledge_registry import (
    KnowledgeAlias,
    KnowledgeCategory,
    KnowledgeCollection,
    KnowledgeRegistryEntry,
    KnowledgeVersionGroup,
)
from app.knowledge_registry.aliases.catalog import CANONICAL_ALIASES
from app.knowledge_registry.enums import CollectionSlug
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_registry.version import REGISTRY_PIPELINE_VERSION

_COLLECTION_NAMES = {
    CollectionSlug.HR.value: "HR",
    CollectionSlug.FINANCE.value: "Finance",
    CollectionSlug.ENGINEERING.value: "Engineering",
    CollectionSlug.IT.value: "IT",
    CollectionSlug.SECURITY.value: "Security",
    CollectionSlug.LEGAL.value: "Legal",
    CollectionSlug.MARKETING.value: "Marketing",
    CollectionSlug.SALES.value: "Sales",
    CollectionSlug.OPERATIONS.value: "Operations",
    CollectionSlug.RESEARCH.value: "Research",
    CollectionSlug.PERSONAL.value: "Personal",
    CollectionSlug.EXTERNAL.value: "External",
    CollectionSlug.SUPPORT.value: "Support",
    CollectionSlug.ADMIN.value: "Admin",
    CollectionSlug.UNKNOWN.value: "Unknown",
}


class KnowledgeRegistryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_seed_data(self) -> None:
        for slug, name in _COLLECTION_NAMES.items():
            existing = (
                self._session.query(KnowledgeCollection)
                .filter(KnowledgeCollection.slug == slug)
                .one_or_none()
            )
            if existing is None:
                self._session.add(
                    KnowledgeCollection(slug=slug, name=name, description=f"{name} knowledge collection")
                )
        for canonical, aliases in CANONICAL_ALIASES.items():
            for alias in aliases:
                normalized = alias.lower()
                exists = (
                    self._session.query(KnowledgeAlias)
                    .filter(KnowledgeAlias.normalized_alias == normalized)
                    .one_or_none()
                )
                if exists is None:
                    self._session.add(
                        KnowledgeAlias(
                            canonical=canonical,
                            alias=alias,
                            normalized_alias=normalized,
                        )
                    )
        self._session.commit()

    def upsert_entry(
        self,
        entry: RegistryEntry,
        *,
        document_knowledge_id: uuid.UUID | None = None,
    ) -> KnowledgeRegistryEntry:
        document_id = uuid.UUID(str(entry.document_id))
        existing = (
            self._session.query(KnowledgeRegistryEntry)
            .filter(KnowledgeRegistryEntry.document_id == document_id)
            .one_or_none()
        )
        version_group_id = None
        if entry.version_group_key:
            group = (
                self._session.query(KnowledgeVersionGroup)
                .filter(KnowledgeVersionGroup.group_key == entry.version_group_key)
                .one_or_none()
            )
            if group is None:
                group = KnowledgeVersionGroup(
                    group_key=entry.version_group_key,
                    canonical_title=entry.filename,
                )
                self._session.add(group)
                self._session.flush()
            version_group_id = group.id

        for path in entry.categories:
            self._ensure_category_path(path, entry.primary_collection)

        duplicate_of_id = None
        if entry.probable_duplicate_of:
            try:
                duplicate_of_id = uuid.UUID(str(entry.probable_duplicate_of))
            except ValueError:
                duplicate_of_id = None

        fields = dict(
            filename=entry.filename,
            document_knowledge_id=document_knowledge_id,
            primary_collection=entry.primary_collection,
            collections_json=json.dumps(entry.collections),
            taxonomy_path=entry.taxonomy_path,
            categories_json=json.dumps(entry.categories),
            canonical_concepts_json=json.dumps(entry.canonical_concepts),
            aliases_json=json.dumps(entry.aliases_applied),
            version_group_id=version_group_id,
            version_group_key=entry.version_group_key,
            version_label=entry.version_label,
            version_rank=entry.version_rank,
            duplicate_of_id=duplicate_of_id,
            duplicate_score=float(entry.duplicate_score),
            health_status=entry.health,
            needs_manual_review=entry.needs_manual_review,
            review_reasons_json=json.dumps(entry.review_reasons),
            registry_json=json.dumps(entry.to_dict()),
            pipeline_version=REGISTRY_PIPELINE_VERSION,
        )

        if existing is None:
            knowledge_id = uuid.UUID(str(entry.knowledge_id)) if entry.knowledge_id else uuid.uuid4()
            record = KnowledgeRegistryEntry(id=knowledge_id, document_id=document_id, **fields)
            self._session.add(record)
            entry.knowledge_id = str(knowledge_id)
        else:
            record = existing
            entry.knowledge_id = str(existing.id)
            for key, value in fields.items():
                setattr(record, key, value)
            # Refresh JSON with stable id
            record.registry_json = json.dumps(entry.to_dict())

        self._session.commit()
        self._session.refresh(record)
        return record

    def list_entries(self, *, limit: int = 500) -> list[KnowledgeRegistryEntry]:
        return (
            self._session.query(KnowledgeRegistryEntry)
            .order_by(KnowledgeRegistryEntry.updated_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_document_id(self, document_id: uuid.UUID | str) -> KnowledgeRegistryEntry | None:
        return (
            self._session.query(KnowledgeRegistryEntry)
            .filter(KnowledgeRegistryEntry.document_id == uuid.UUID(str(document_id)))
            .one_or_none()
        )

    def peers_as_entries(self, *, exclude_document_id: str | None = None) -> list[RegistryEntry]:
        rows = self.list_entries(limit=1000)
        result: list[RegistryEntry] = []
        for row in rows:
            if exclude_document_id and str(row.document_id) == str(exclude_document_id):
                continue
            data = row.registry_dict()
            if data.get("knowledge_id"):
                result.append(
                    RegistryEntry(
                        knowledge_id=str(row.id),
                        document_id=str(row.document_id),
                        filename=row.filename,
                        collections=json.loads(row.collections_json or "[]"),
                        primary_collection=row.primary_collection,
                        taxonomy_path=row.taxonomy_path,
                        categories=json.loads(row.categories_json or "[]"),
                        canonical_concepts=json.loads(row.canonical_concepts_json or "[]"),
                        version_group_key=row.version_group_key,
                        version_label=row.version_label,
                        version_rank=row.version_rank,
                        health=row.health_status,
                    )
                )
        return result

    def _ensure_category_path(self, path: str, collection_slug: str) -> None:
        existing = (
            self._session.query(KnowledgeCategory)
            .filter(KnowledgeCategory.path == path)
            .one_or_none()
        )
        if existing is not None:
            return
        parts = path.split("/")
        parent_id = None
        built = []
        for depth, part in enumerate(parts):
            built.append(part)
            current_path = "/".join(built)
            row = (
                self._session.query(KnowledgeCategory)
                .filter(KnowledgeCategory.path == current_path)
                .one_or_none()
            )
            if row is None:
                row = KnowledgeCategory(
                    collection_slug=collection_slug,
                    parent_id=parent_id,
                    slug=part.lower().replace(" ", "-"),
                    name=part,
                    path=current_path,
                    depth=depth,
                )
                self._session.add(row)
                self._session.flush()
            parent_id = row.id
