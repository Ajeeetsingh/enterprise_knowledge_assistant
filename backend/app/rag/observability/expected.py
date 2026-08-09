"""Expected-chunk signatures for acceptance diagnostics (not used for ranking)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from app.rag.observability.models import ExpectedChunkVerdict, chunk_preview


@dataclass(frozen=True)
class ExpectedSignature:
    label: str
    # All patterns must match (case-insensitive) within the same chunk.
    must_contain: tuple[str, ...]
    preferred_source_substr: tuple[str, ...] = ()


# Acceptance questions → content signatures that should appear in grounded answers.
ACCEPTANCE_EXPECTATIONS: dict[str, tuple[ExpectedSignature, ...]] = {
    "mission": (
        # Prefer distinctive wording from Company Profile §1.4 / §1.5 / §1.6.
        # Loose tokens like "mission"+"steward" false-match Finance "steward capital".
        ExpectedSignature(
            label="Mission statement",
            must_contain=("1.4 mission",),
            preferred_source_substr=("company_profile", "company profile"),
        ),
        ExpectedSignature(
            label="Mission statement (body)",
            must_contain=("mission", "apex national bank exists"),
            preferred_source_substr=("company_profile", "company profile"),
        ),
        ExpectedSignature(
            label="Vision statement",
            must_contain=("1.5 vision",),
            preferred_source_substr=("company_profile", "company profile"),
        ),
        ExpectedSignature(
            label="Core values section",
            must_contain=("1.6 core values", "client stewardship"),
            preferred_source_substr=("company_profile", "company profile"),
        ),
    ),
    "metadata": (
        ExpectedSignature(
            label="Metadata categories (seven)",
            must_contain=("seven categories", "metadata at apex"),
            preferred_source_substr=("metadata",),
        ),
        ExpectedSignature(
            label="Metadata taxonomy section",
            must_contain=("4 metadata taxonomy", "seven categories"),
            preferred_source_substr=("metadata",),
        ),
    ),
    "taxonomy": (
        ExpectedSignature(
            label="Four-level hierarchy",
            must_contain=("exactly four levels", "l1 domain"),
            preferred_source_substr=("taxonomy", "knowledge_taxonomy"),
        ),
        ExpectedSignature(
            label="L1-L4 structure",
            must_contain=("l1 domain", "l2 category", "l3 sub-category"),
            preferred_source_substr=("taxonomy", "knowledge_taxonomy"),
        ),
    ),
    "bpc": (
        ExpectedSignature(
            label="Document purpose connections",
            must_contain=("documents connect", "systems"),
            preferred_source_substr=("business_process", "process_classification"),
        ),
        ExpectedSignature(
            label="Mandatory mappings",
            must_contain=("mandatory mapping", "process"),
            preferred_source_substr=("business_process", "process_classification"),
        ),
    ),
}


def select_expectation_key(question: str) -> str | None:
    lowered = question.lower()
    if "mission" in lowered or "core values" in lowered or "vision" in lowered:
        return "mission"
    if "metadata" in lowered:
        return "metadata"
    if "taxonomy" in lowered or "hierarchy" in lowered:
        return "taxonomy"
    if "business process" in lowered or "process classification" in lowered:
        return "bpc"
    return None


def _chunk_text(chunk: Any) -> str:
    return (getattr(chunk, "content", None) or "").lower()


def _chunk_source(chunk: Any) -> str:
    return (getattr(chunk, "source", None) or "").lower()


def find_expected_chunk(
    chunks: Iterable[Any],
    signature: ExpectedSignature,
) -> Any | None:
    """Return the best indexed chunk matching *signature*, or None."""
    patterns = [re.compile(re.escape(p.lower())) for p in signature.must_contain]
    preferred = [p.lower() for p in signature.preferred_source_substr]
    candidates: list[tuple[int, Any]] = []
    for chunk in chunks:
        text = _chunk_text(chunk)
        if not text:
            continue
        if not all(p.search(text) for p in patterns):
            continue
        source = _chunk_source(chunk)
        boost = 1 if any(token in source for token in preferred) else 0
        candidates.append((boost, chunk))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], getattr(item[1], "chunk_id", "")))
    return candidates[0][1]


def _rank_in(ids: list[str], chunk_id: str) -> int | None:
    try:
        return ids.index(chunk_id) + 1
    except ValueError:
        return None


def _signature_in_texts(signature: ExpectedSignature, texts: Iterable[str]) -> bool:
    patterns = [re.compile(re.escape(p.lower())) for p in signature.must_contain]
    for text in texts:
        lowered = (text or "").lower()
        if lowered and all(p.search(lowered) for p in patterns):
            return True
    return False


def evaluate_expected_chunks(
    *,
    question: str,
    indexed_chunks: Iterable[Any],
    stages: dict[str, list[str]],
    final_chunk_ids: list[str],
    rerank_chunk_ids: list[str],
    merge_chunk_ids: list[str],
    final_chunk_texts: list[str] | None = None,
) -> list[ExpectedChunkVerdict]:
    """Compare expected signatures against stage membership."""
    key = select_expectation_key(question)
    if key is None:
        return []
    signatures = ACCEPTANCE_EXPECTATIONS.get(key, ())
    verdicts: list[ExpectedChunkVerdict] = []
    final_texts = list(final_chunk_texts or [])

    for signature in signatures:
        match = find_expected_chunk(indexed_chunks, signature)
        if match is None:
            # Still detect if equivalent wording reached the LLM via another chunk.
            if final_texts and _signature_in_texts(signature, final_texts):
                verdicts.append(
                    ExpectedChunkVerdict(
                        label=signature.label,
                        signature=" + ".join(signature.must_contain),
                        expected_chunk_id=None,
                        expected_document=None,
                        expected_page=None,
                        expected_preview=None,
                        retrieved=True,
                        best_rank=None,
                        fate="equivalent_content_in_final_context",
                        stages_seen=["final"],
                    )
                )
            else:
                verdicts.append(
                    ExpectedChunkVerdict(
                        label=signature.label,
                        signature=" + ".join(signature.must_contain),
                        expected_chunk_id=None,
                        expected_document=None,
                        expected_page=None,
                        expected_preview=None,
                        retrieved=False,
                        best_rank=None,
                        fate="never_indexed_or_signature_miss",
                        stages_seen=[],
                    )
                )
            continue

        chunk_id = match.chunk_id
        stages_seen = [name for name, ids in stages.items() if chunk_id in ids]
        in_final = chunk_id in final_chunk_ids
        in_rerank = chunk_id in rerank_chunk_ids
        in_merge = chunk_id in merge_chunk_ids
        equiv_in_final = (not in_final) and bool(final_texts) and _signature_in_texts(
            signature, final_texts
        )

        # Prefer the latest stage rank when available (final > rerank > merge).
        if in_final:
            fate = "found_in_final_context"
            best_rank = _rank_in(final_chunk_ids, chunk_id)
            retrieved = True
        elif equiv_in_final:
            fate = "equivalent_content_in_final_context"
            best_rank = _rank_in(final_chunk_ids, chunk_id)  # usually None
            retrieved = True
            if "final" not in stages_seen:
                stages_seen.append("final")
        elif in_rerank:
            fate = "removed_during_context_building"
            best_rank = _rank_in(rerank_chunk_ids, chunk_id)
            retrieved = True
        elif in_merge:
            fate = "removed_during_reranking"
            best_rank = _rank_in(merge_chunk_ids, chunk_id)
            retrieved = True
        elif any(name in stages_seen for name in ("fusion", "dense", "bm25", "per_query")):
            # Seen in a per-query stage but dropped before multi-query merge.
            fate = "removed_during_fusion"
            best_rank = (
                _rank_in(stages.get("per_query", []), chunk_id)
                or _rank_in(stages.get("fusion", []), chunk_id)
                or _rank_in(stages.get("dense", []), chunk_id)
                or _rank_in(stages.get("bm25", []), chunk_id)
            )
            retrieved = True
        elif stages_seen:
            fate = "retrieved_but_discarded"
            best_rank = None
            retrieved = True
        else:
            fate = "never_retrieved"
            best_rank = None
            retrieved = False

        verdicts.append(
            ExpectedChunkVerdict(
                label=signature.label,
                signature=" + ".join(signature.must_contain),
                expected_chunk_id=chunk_id,
                expected_document=getattr(match, "source", None),
                expected_page=getattr(match, "page_number", None),
                expected_preview=chunk_preview(getattr(match, "content", "")),
                retrieved=retrieved,
                best_rank=best_rank,
                fate=fate,
                stages_seen=stages_seen,
            )
        )
    return verdicts
