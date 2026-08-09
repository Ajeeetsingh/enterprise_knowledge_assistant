"""End-to-end stage trace for mission/vision/core-values regression.

Does not change ranking — instrumentation only.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

QUERY = "What is Apex National Bank's mission, vision, and core values?"
TARGETS = {
    "mission": "COMPANY_PROFILE.pdf::sem-h267-p268",
    "vision": "COMPANY_PROFILE.pdf::sem-h271-p272",
    "core": "COMPANY_PROFILE.pdf::sem-h276",
    "core_table": "COMPANY_PROFILE.pdf::sem-table-276",
}


def _safe(s: object) -> str:
    return str(s).encode("ascii", "replace").decode("ascii")


def _preview(text: str | None, n: int = 150) -> str:
    return _safe((text or "").replace("\n", " ")[:n])


def _is_target(chunk_id: str, label: str) -> bool:
    cid = TARGETS[label]
    if chunk_id == cid:
        return True
    if label == "core" and chunk_id.startswith("COMPANY_PROFILE.pdf::sem-h276"):
        return True
    if label == "core_table" and chunk_id.startswith("COMPANY_PROFILE.pdf::sem-table-276"):
        return True
    return False


def _mark(chunk_id: str) -> str:
    for label in TARGETS:
        if _is_target(chunk_id, label):
            return f"*** {label.upper()} ***"
    return ""


def main() -> int:
    from app.config import get_settings
    from app.core.logging import setup_logging
    from app.db.session import SessionLocal
    from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
    from app.documents.status import DocumentStatus
    from app.services.document_service import get_document_service
    from app.services.index_bootstrap_service import bootstrap_search_index
    from app.rag.hybrid.index_store import HybridIndexStore
    from app.rag.hybrid.retriever import HybridRetriever
    from app.rag.hybrid.config import HybridRetrievalSettings
    from app.rag.metadata_retrieval.retriever import MetadataAwareRetriever
    from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
    from app.rag.query_processing import QueryProcessor, merge_multi_query_results
    from app.rag.query_processing.strategy import (
        apply_strategy_to_hybrid_settings,
        apply_strategy_to_metadata_settings,
        apply_strategy_to_rerank_settings,
    )
    from app.rag.reranking import CrossEncoderReranker
    from app.rag.reranking.config import RerankingSettings
    from app.rag.engine import (
        _expand_exhaustive_context,
        _resolve_context_top_k,
        _collect_focus_document_chunks,
    )
    from app.llm.prompt_builder import PromptBuilder
    from app.llm.factory import create_llm_provider
    from app.llm.types import LLMGenerationRequest

    setup_logging()
    settings = get_settings()
    doc_service = get_document_service()
    with SessionLocal() as session:
        bootstrap_search_index(session, doc_service)
        docs, _ = DocumentRepository(session).list(
            limit=10_000,
            offset=0,
            filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
        )
        sources = {d.filename for d in docs if d.filename}

    store = doc_service.vector_store
    faiss = store.faiss_store if isinstance(store, HybridIndexStore) else store
    bm25 = store.bm25_index if isinstance(store, HybridIndexStore) else None

    # Confirm targets indexed
    print("=" * 60)
    print("INDEX CHECK")
    print("=" * 60)
    indexed = {c.chunk_id: c for c in faiss.chunks}
    for label, cid in TARGETS.items():
        hits = [k for k in indexed if _is_target(k, label)]
        print(f"{label}: indexed={bool(hits)} ids={hits[:3] or [cid]}")
        for k in hits[:1]:
            print(" ", _preview(indexed[k].content, 200))

    processor = QueryProcessor()
    outcome = processor.process(QUERY)
    print("\nclassification", outcome.classification.category)
    print("retrieval_queries:")
    for q in outcome.retrieval_queries:
        print(" -", _safe(q))

    hybrid = apply_strategy_to_hybrid_settings(
        HybridRetrievalSettings.from_settings(), outcome.strategy
    )
    meta = apply_strategy_to_metadata_settings(
        MetadataRetrievalSettings.from_settings(), outcome.strategy
    )
    rerank_s = apply_strategy_to_rerank_settings(
        RerankingSettings.from_settings(), outcome.strategy
    )
    context_top_k = _resolve_context_top_k(outcome.classification.category)
    fetch_k = rerank_s.rerank_top_n if rerank_s.enabled else context_top_k
    print(f"\nrerank_top_n={rerank_s.rerank_top_n} context_top_k={context_top_k} fetch_k={fetch_k}")

    retriever = HybridRetriever(
        settings=hybrid,
        metadata_retriever=MetadataAwareRetriever(settings=meta),
    )

    # Stage 1: per-query hybrid
    print("\n" + "=" * 60)
    print("STAGE 1 — HYBRID RETRIEVAL (per expanded query)")
    print("=" * 60)
    per_query_results = []
    origins: dict[str, set[str]] = {}
    for rq in outcome.retrieval_queries:
        hits = retriever.search(
            faiss, bm25, rq, top_k=fetch_k, allowed_sources=sources
        )
        per_query_results.append(hits)
        origin = "original" if rq == outcome.retrieval_queries[0] else "expansion"
        print(f"\nQuery ({origin}): {_safe(rq)!r}")
        for rank, item in enumerate(hits[:15], start=1):
            mark = _mark(item.chunk_id)
            print(
                f"  #{rank} {item.chunk_id} p{item.page_number} "
                f"score={item.final_score or item.confidence} {mark}"
            )
            print(f"     {_preview(item.content)}")
            origins.setdefault(item.chunk_id, set()).add(origin)
        for label in TARGETS:
            found = next(
                (
                    (i + 1, h)
                    for i, h in enumerate(hits)
                    if _is_target(h.chunk_id, label)
                ),
                None,
            )
            print(
                f"  TARGET {label}:",
                f"rank={found[0]}" if found else "ABSENT",
            )

    # Stage 2: merge
    print("\n" + "=" * 60)
    print("STAGE 2 — MERGE OUTPUT")
    print("=" * 60)
    merged = merge_multi_query_results(per_query_results, limit=fetch_k)
    for rank, item in enumerate(merged, start=1):
        mark = _mark(item.chunk_id)
        origin = origins.get(item.chunk_id, set())
        if "original" in origin and "expansion" in origin:
            origin_s = "both"
        elif "original" in origin:
            origin_s = "original query"
        elif "expansion" in origin:
            origin_s = "expansion"
        else:
            origin_s = "unknown"
        print(
            f"#{rank} {item.chunk_id} merged_score={item.final_score or item.confidence} "
            f"origin={origin_s} {mark}"
        )
        print(f"   {_preview(item.content)}")

    print("\nTARGET PRESENCE AFTER MERGE:")
    for label, cid in TARGETS.items():
        hit = next(
            (
                (i + 1, h)
                for i, h in enumerate(merged)
                if _is_target(h.chunk_id, label)
            ),
            None,
        )
        print(f"  {label} ({cid}):", f"rank={hit[0]}" if hit else "MISSING")

    # Stage 3/4: CrossEncoder
    print("\n" + "=" * 60)
    print("STAGE 3 — CROSSENCODER INPUT")
    print("=" * 60)
    pool = merged[: rerank_s.rerank_top_n]
    print(f"pool_size={len(pool)} (rerank_top_n={rerank_s.rerank_top_n})")
    for rank, item in enumerate(pool, start=1):
        print(f"  IN #{rank} {item.chunk_id} {_mark(item.chunk_id)}")

    print("\n" + "=" * 60)
    print("STAGE 4 — CROSSENCODER OUTPUT")
    print("=" * 60)
    reranker = CrossEncoderReranker(
        settings=rerank_s,
        metadata_bonus_reference=meta.max_metadata_bonus,
    )
    reranked = reranker.rerank(QUERY, merged, top_k=context_top_k)
    # Also get full pool ranking for visibility
    full_reranked = reranker.rerank(QUERY, merged, top_k=len(pool))
    for rank, item in enumerate(full_reranked, start=1):
        mark = _mark(item.chunk_id)
        in_top = "KEEP" if rank <= context_top_k else "CUT_BY_top_k"
        print(
            f"#{rank} {item.chunk_id} ce={item.reranker_score} "
            f"final={item.final_score} {in_top} {mark}"
        )
        print(f"   {_preview(item.content)}")

    print("\nTARGET PRESENCE AFTER CE (full pool order):")
    for label in TARGETS:
        hit = next(
            (
                (i + 1, h)
                for i, h in enumerate(full_reranked)
                if _is_target(h.chunk_id, label)
            ),
            None,
        )
        if hit:
            rank, item = hit
            kept = rank <= context_top_k
            print(
                f"  {label}: CE_rank={rank} ce={item.reranker_score} "
                f"kept_in_top_k={kept} (top_k={context_top_k})"
            )
        else:
            print(f"  {label}: NOT IN CE POOL")

    # Stage 5: context builder
    print("\n" + "=" * 60)
    print("STAGE 5 — CONTEXT BUILDER")
    print("=" * 60)
    print(
        f"category={outcome.classification.category} "
        f"wants_exec_list_expansion=check via function"
    )
    from app.rag.engine import _query_wants_executive_leaders, _query_wants_strategic_priorities

    wants = _query_wants_executive_leaders(QUERY) or _query_wants_strategic_priorities(QUERY)
    print(f"_query_wants_executive_leaders/strategic={wants}")
    print(
        "expansion path:",
        "exhaustive" if (
            outcome.classification.category.value in {"list", "table"} and wants
        ) else "reranked[:top_k] only",
    )

    focus_source_chunks = None
    if outcome.classification.category.value in {"list", "table"} and reranked and wants:
        source_scores: dict[str, float] = {}
        for item in reranked[:10]:
            score = item.reranker_score if item.reranker_score is not None else item.confidence
            source_scores[item.source] = source_scores.get(item.source, 0.0) + score
        focus_source = max(source_scores, key=source_scores.get)
        focus_source_chunks = _collect_focus_document_chunks(faiss, focus_source, merged)
        print(f"focus_source={focus_source} focus_chunks={len(focus_source_chunks)}")

    final_context = _expand_exhaustive_context(
        reranked,
        merged,
        top_k=context_top_k,
        category=outcome.classification.category,
        focus_source_chunks=focus_source_chunks,
        query=QUERY,
    )
    print("\nSELECTED FOR LLM:")
    selected_ids = {c.chunk_id for c in final_context}
    for order, item in enumerate(final_context, start=1):
        print(
            f"  Chunk {order}: {item.chunk_id} p{item.page_number} {_mark(item.chunk_id)}"
        )
        print(f"    {_preview(item.content, 200)}")

    print("\nDISCARDED TARGET ANALYSIS:")
    for label in TARGETS:
        candidates = [h for h in full_reranked if _is_target(h.chunk_id, label)]
        if not candidates:
            in_merge = any(_is_target(h.chunk_id, label) for h in merged)
            if not in_merge:
                print(
                    f"  {label}: removed in merge_multi_query_results "
                    f"(backend/app/rag/query_processing/multi_query.py) — "
                    f"not in merged[:fetch_k={fetch_k}] "
                    f"(may be skipped as low-information stub)"
                )
            else:
                print(
                    f"  {label}: removed before CE pool "
                    f"(CrossEncoderReranker.rerank pool = merged[:rerank_top_n])"
                )
            continue
        item = candidates[0]
        rank = next(
            i + 1
            for i, h in enumerate(full_reranked)
            if h.chunk_id == item.chunk_id
        )
        if item.chunk_id in selected_ids:
            print(f"  {label}: PRESENT in final context")
            continue
        if rank > context_top_k:
            print(
                f"  {label}: removed by CrossEncoderReranker.rerank return slice "
                f"reranked[:top_k] where top_k=context_top_k={context_top_k}; "
                f"CE_rank={rank} ce={item.reranker_score} final={item.final_score}"
            )
            print(
                "    function: CrossEncoderReranker.rerank "
                "(backend/app/rag/reranking/reranker.py return reranked[:top_k])"
            )
            print(
                "    also: apply_reranker_scores ranking "
                "(backend/app/rag/reranking/scorer.py) produced this CE_rank"
            )
            continue
        print(
            f"  {label}: was CE_rank={rank} (<= top_k) but missing from final context"
        )
        print(
            "    function: _expand_exhaustive_context "
            "(backend/app/rag/engine.py)"
        )

    # Stage 6: prompt
    print("\n" + "=" * 60)
    print("STAGE 6 — COMPLETE PROMPT")
    print("=" * 60)
    builder = PromptBuilder()
    prompt = builder.build(QUERY, final_context)
    full_prompt = f"{prompt.system}\n\n{prompt.user}"
    print(full_prompt)
    print("\n[END PROMPT]")
    print("prompt_length", prompt.total_length)

    # Stage 7: LLM
    print("\n" + "=" * 60)
    print("STAGE 7 — LLM RESPONSE")
    print("=" * 60)
    provider = create_llm_provider(settings)
    if provider is None:
        print("No LLM provider configured")
        return 0
    request = LLMGenerationRequest(
        question=QUERY,
        retrieved_chunks=final_context,
        conversation_history=None,
        prompt=prompt,
    )
    result = provider.generate_sync(request)
    print("RAW:", _safe(result.answer))
    print("model:", result.model, "provider:", result.provider_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
