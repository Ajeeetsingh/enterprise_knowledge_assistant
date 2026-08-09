"""Knowledge Registry orchestrator (Phase 13.2)."""

from __future__ import annotations

import uuid
from collections import defaultdict

from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_registry.aliases.normalizer import AliasNormalizer
from app.knowledge_registry.collections.assigner import CollectionAssigner
from app.knowledge_registry.duplicates.detector import DuplicateDetector
from app.knowledge_registry.health.assessor import HealthAssessor
from app.knowledge_registry.statistics import build_statistics
from app.knowledge_registry.taxonomy.builder import TaxonomyBuilder
from app.knowledge_registry.types import RegistryEntry, RegistryStatistics
from app.knowledge_registry.version import REGISTRY_PIPELINE_VERSION
from app.knowledge_registry.versions.detector import VersionDetector


class KnowledgeRegistryService:
    """Organize Knowledge Objects into the Enterprise Knowledge Registry.

    Pure domain orchestration — persistence is optional via ``KnowledgeRegistryRepository``.
    """

    def __init__(
        self,
        *,
        collections: CollectionAssigner | None = None,
        taxonomy: TaxonomyBuilder | None = None,
        aliases: AliasNormalizer | None = None,
        versions: VersionDetector | None = None,
        duplicates: DuplicateDetector | None = None,
        health: HealthAssessor | None = None,
    ) -> None:
        self._collections = collections or CollectionAssigner()
        self._taxonomy = taxonomy or TaxonomyBuilder()
        self._aliases = aliases or AliasNormalizer()
        self._versions = versions or VersionDetector()
        self._duplicates = duplicates or DuplicateDetector()
        self._health = health or HealthAssessor()

    def build_entry(
        self,
        knowledge: DocumentKnowledge,
        *,
        knowledge_id: str | None = None,
        peers: list[RegistryEntry] | None = None,
        latest_rank_by_group: dict[str, int] | None = None,
    ) -> RegistryEntry:
        collections = self._collections.assign(knowledge)
        primary = collections[0]
        canons, applied = self._aliases.normalize_knowledge(knowledge)
        taxonomy_path, nodes = self._taxonomy.build(
            knowledge,
            primary_collection=primary,
            canonical_concepts=canons,
        )
        group_key, version_label, version_rank = self._versions.detect(knowledge)

        entry = RegistryEntry(
            knowledge_id=knowledge_id or str(uuid.uuid4()),
            document_id=knowledge.document_id,
            filename=knowledge.metadata.filename,
            collections=collections,
            primary_collection=primary,
            taxonomy_path=taxonomy_path,
            categories=[node.path for node in nodes],
            canonical_concepts=canons,
            aliases_applied=applied,
            version_group_key=group_key,
            version_label=version_label,
            version_rank=version_rank,
        )

        if peers:
            signal = self._duplicates.find_duplicates(entry, peers)
            if signal:
                entry.probable_duplicate_of = signal.other_knowledge_id
                entry.duplicate_score = signal.score

        latest_rank = (latest_rank_by_group or {}).get(group_key, version_rank)
        is_latest = version_rank >= latest_rank
        health, review, reasons = self._health.assess(
            knowledge,
            entry,
            is_latest_in_group=is_latest,
        )
        entry.health = health
        entry.needs_manual_review = review
        entry.review_reasons = reasons
        return entry

    def register_many(self, knowledge_objects: list[DocumentKnowledge]) -> list[RegistryEntry]:
        """Offline / validation path — register a batch with cross-document signals."""
        prelim: list[RegistryEntry] = []
        ranks: dict[str, int] = defaultdict(int)
        for knowledge in knowledge_objects:
            collections = self._collections.assign(knowledge)
            canons, applied = self._aliases.normalize_knowledge(knowledge)
            taxonomy_path, nodes = self._taxonomy.build(
                knowledge,
                primary_collection=collections[0],
                canonical_concepts=canons,
            )
            group_key, version_label, version_rank = self._versions.detect(knowledge)
            ranks[group_key] = max(ranks[group_key], version_rank)
            prelim.append(
                RegistryEntry(
                    knowledge_id=str(uuid.uuid4()),
                    document_id=knowledge.document_id,
                    filename=knowledge.metadata.filename,
                    collections=collections,
                    primary_collection=collections[0],
                    taxonomy_path=taxonomy_path,
                    categories=[node.path for node in nodes],
                    canonical_concepts=canons,
                    aliases_applied=applied,
                    version_group_key=group_key,
                    version_label=version_label,
                    version_rank=version_rank,
                )
            )

        final: list[RegistryEntry] = []
        for knowledge, draft in zip(knowledge_objects, prelim, strict=True):
            entry = self.build_entry(
                knowledge,
                knowledge_id=draft.knowledge_id,
                peers=prelim,
                latest_rank_by_group=dict(ranks),
            )
            final.append(entry)
        return final

    def statistics(self, entries: list[RegistryEntry]) -> RegistryStatistics:
        return build_statistics(entries)

    @property
    def pipeline_version(self) -> str:
        return REGISTRY_PIPELINE_VERSION
