"""Probable knowledge-duplicate detection (beyond checksum)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.knowledge_registry.types import RegistryEntry

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class DuplicateSignal:
    other_knowledge_id: str
    other_filename: str
    score: float
    reason: str


class DuplicateDetector:
    """Compare registry entries for probable knowledge duplicates / versions."""

    def find_duplicates(
        self,
        entry: RegistryEntry,
        peers: list[RegistryEntry],
        *,
        threshold: float = 0.72,
    ) -> DuplicateSignal | None:
        best: DuplicateSignal | None = None
        for peer in peers:
            if peer.knowledge_id == entry.knowledge_id:
                continue
            score, reason = self._score(entry, peer)
            if score < threshold:
                continue
            if best is None or score > best.score:
                best = DuplicateSignal(
                    other_knowledge_id=peer.knowledge_id,
                    other_filename=peer.filename,
                    score=round(score, 3),
                    reason=reason,
                )
        return best

    def _score(self, left: RegistryEntry, right: RegistryEntry) -> tuple[float, str]:
        if left.version_group_key and left.version_group_key == right.version_group_key:
            return 0.95, "same_version_group"

        left_tokens = self._tokens(left.filename)
        right_tokens = self._tokens(right.filename)
        if not left_tokens or not right_tokens:
            return 0.0, "insufficient_tokens"
        overlap = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        jaccard = overlap / union if union else 0.0

        same_collection = left.primary_collection == right.primary_collection
        same_taxonomy = bool(left.taxonomy_path and left.taxonomy_path == right.taxonomy_path)
        bonus = 0.15 if same_collection else 0.0
        bonus += 0.1 if same_taxonomy else 0.0
        score = min(0.99, jaccard + bonus)
        reason = "filename_similarity"
        if same_taxonomy:
            reason = "taxonomy_and_filename"
        return score, reason

    def _tokens(self, filename: str) -> set[str]:
        stem = Path(filename).stem.lower()
        stem = re.sub(r"(final|draft|copy|v\d+|rev\d+)", " ", stem)
        stop = {"policy", "policies", "report", "reports", "doc", "document", "acme"}
        return {token for token in _TOKEN_RE.findall(stem) if len(token) > 2 and token not in stop}
