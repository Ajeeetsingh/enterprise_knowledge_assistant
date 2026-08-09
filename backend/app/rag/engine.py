"""Enterprise RAG orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.ingestion.loader import load_documents
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.llm.base import LLMProvider
from app.llm.exceptions import LLMError
from app.llm.prompt_builder import PromptBuilder
from app.llm.types import GenerationOutcome, LLMGenerationRequest
from app.rag.answer_generator import AnswerGenerator
from app.rag.rbac import check_access, get_accessible_categories, validate_role
from app.rag.metadata_retrieval import MetadataAwareRetriever
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.hybrid import BM25Index, HybridIndexStore, HybridRetriever
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.reranking import CrossEncoderReranker
from app.rag.reranking.config import RerankingSettings
from app.rag.query_processing import QueryProcessor, merge_multi_query_results
from app.rag.query_processing.schemas import QueryCategory
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.strategy import (
    apply_strategy_to_hybrid_settings,
    apply_strategy_to_metadata_settings,
    apply_strategy_to_rerank_settings,
)
from app.rag.retriever import SemanticRetriever
from app.rag.router import route_query
from app.rag.types import CITATION_EXCERPT_LENGTH, Citation, QueryResponse, RetrievalResult
from app.query_router.messages import INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE

logger = get_logger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"


def _resolve_context_top_k(
    category: QueryCategory | None,
    *,
    explicit_top_k: int | None = None,
) -> int:
    """Resolve how many chunks to send to the LLM for the current query."""
    if explicit_top_k is not None:
        return explicit_top_k
    settings = get_settings()
    if category in (QueryCategory.LIST, QueryCategory.TABLE):
        return max(settings.top_k_final, 8)
    # Multi-aspect definition questions (e.g. mission + vision + values) need a
    # wider context window: CE often ranks document mastheads above body sections
    # that still sit inside the rerank pool (mission/vision regression: answers at
    # CE ranks 9–12 were cut by top_k=5).
    if category == QueryCategory.DEFINITION:
        return max(settings.top_k_final, 12)
    return settings.top_k_final


def _query_wants_strategic_priorities(query: str) -> bool:
    lowered = query.lower()
    return any(
        marker in lowered
        for marker in ("strategic", "priorit", "fy2026", "fy 2026")
    )


def _query_wants_executive_leaders(query: str) -> bool:
    lowered = query.lower()
    return any(
        marker in lowered
        for marker in (
            "executive",
            "leader",
            "leadership",
            "chief ",
            " cto",
            " cfo",
            " ceo",
            " coo",
            " cco",
            " ciso",
            "officer",
        )
    )


def _expand_exhaustive_context(
    reranked: list[RetrievalResult],
    candidates: list[RetrievalResult],
    *,
    top_k: int,
    category: QueryCategory | None,
    focus_source_chunks: list[RetrievalResult] | None = None,
    query: str = "",
) -> list[RetrievalResult]:
    """Optionally expand list/table context from the focus document.

    Exhaustive same-document expansion is only applied for executive-leader and
    strategic-priority list intents. For other LIST/TABLE queries (e.g. metadata
    categories), CrossEncoder order is preserved — Phase 3B diagnostics showed
    generic list expansion reordered CE winners behind unrelated FAISS chunks
    sorted by chunk_id, dropping the correct evidence from the prompt.
    """
    if category not in (QueryCategory.LIST, QueryCategory.TABLE) or not reranked:
        return reranked[:top_k]

    wants_exhaustive = _query_wants_executive_leaders(query) or _query_wants_strategic_priorities(
        query
    )
    if not wants_exhaustive:
        return reranked[:top_k]

    source_scores: dict[str, float] = {}
    for item in reranked[:10]:
        score = item.reranker_score if item.reranker_score is not None else item.confidence
        source_scores[item.source] = source_scores.get(item.source, 0.0) + score
    focus_source = max(source_scores, key=source_scores.get)

    selected: list[RetrievalResult] = []
    seen: set[str] = set()
    supplemental = list(candidates)
    if focus_source_chunks:
        supplemental.extend(focus_source_chunks)

    focus_pool: list[RetrievalResult] = []
    focus_seen: set[str] = set()
    for item in reranked:
        if item.source == focus_source and item.chunk_id not in focus_seen:
            focus_pool.append(item)
            focus_seen.add(item.chunk_id)
    for item in supplemental:
        if item.source == focus_source and item.chunk_id not in focus_seen:
            focus_pool.append(item)
            focus_seen.add(item.chunk_id)

    focus_pool.sort(
        key=lambda item: _focus_chunk_priority(item, category, query),
    )
    for item in focus_pool:
        if len(selected) >= top_k:
            break
        if item.chunk_id not in seen:
            selected.append(item)
            seen.add(item.chunk_id)

    for item in reranked:
        if len(selected) >= top_k:
            break
        if item.chunk_id not in seen:
            selected.append(item)
            seen.add(item.chunk_id)

    return selected[:top_k]


def _focus_chunk_priority(
    result: RetrievalResult,
    category: QueryCategory | None,
    query: str = "",
) -> tuple[int, str]:
    """Rank same-document chunks so list/table answers surface complete sections first.

    Priority is derived only from each chunk's own content against the query's
    detected intent — never from chunk IDs, which are assigned per-ingestion
    and carry no meaning across documents.
    """
    content = result.content.lower()
    wants_exec = _query_wants_executive_leaders(query)
    wants_strategic = _query_wants_strategic_priorities(query)

    if category == QueryCategory.LIST and wants_exec:
        if any(
            marker in content
            for marker in (
                "chief executive officer",
                "chief operating officer",
                "chief financial officer",
                "chief technology officer",
                "chief compliance officer",
                "chief information security officer",
            )
        ):
            return (0, result.chunk_id)
        if "executive leadership" in content:
            return (1, result.chunk_id)
        if "strategic priorit" in content:
            return (5, result.chunk_id)

    if category in (QueryCategory.LIST, QueryCategory.TABLE) and wants_strategic:
        if "strategic priorit" in content:
            return (0, result.chunk_id)
        if "table of contents" in content:
            return (4, result.chunk_id)

    return (3, result.chunk_id)


def _collect_focus_document_chunks(
    faiss_store,
    focus_source: str,
    candidates: list[RetrievalResult],
) -> list[RetrievalResult]:
    """Return all indexed chunks from the focus document for list-context expansion."""
    ordered: list[RetrievalResult] = []
    seen: set[str] = set()

    for item in candidates:
        if item.source == focus_source and item.chunk_id not in seen:
            ordered.append(item)
            seen.add(item.chunk_id)

    for chunk in faiss_store.chunks:
        if chunk.source != focus_source or chunk.chunk_id in seen:
            continue
        ordered.append(
            RetrievalResult(
                content=chunk.content,
                source=chunk.source,
                category=chunk.category,
                confidence=0.0,
                chunk_id=chunk.chunk_id,
                page_number=getattr(chunk, "page_number", None),
            )
        )
        seen.add(chunk.chunk_id)

    return ordered


def _log_retrieval_pipeline_debug(
    *,
    query: str,
    category: str | None,
    context_top_k: int,
    candidates: list[RetrievalResult],
    final_results: list[RetrievalResult],
) -> None:
    """Emit structured retrieval trace logs for diagnosing context loss."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    log_with_fields(
        logger,
        logging.DEBUG,
        "RAG retrieval pipeline trace",
        query=query,
        intent=category,
        context_top_k=context_top_k,
        candidate_count=len(candidates),
        candidate_chunks=[
            {
                "chunk_id": item.chunk_id,
                "source": item.source,
                "confidence": item.confidence,
                "reranker_score": item.reranker_score,
            }
            for item in candidates[:15]
        ],
        final_chunks=[
            {
                "chunk_id": item.chunk_id,
                "source": item.source,
                "confidence": item.confidence,
                "reranker_score": item.reranker_score,
                "chars": len(item.content),
            }
            for item in final_results
        ],
    )


def _build_citations(results: list[RetrievalResult]) -> list[Citation]:
    seen_sources: set[str] = set()
    citations: list[Citation] = []

    for result in results:
        if result.source in seen_sources:
            continue
        seen_sources.add(result.source)
        excerpt = result.content[:CITATION_EXCERPT_LENGTH].strip()
        if len(result.content) > CITATION_EXCERPT_LENGTH:
            excerpt += "..."
        citations.append(
            Citation(
                source=result.source,
                excerpt=excerpt,
                confidence=result.confidence,
                page=result.page_number,
            )
        )

    return citations


def _collect_sources(results: list[RetrievalResult]) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for result in results:
        if result.source not in seen:
            seen.add(result.source)
            sources.append(result.source)
    return sources


def _provider_display_name(provider_name: str) -> str:
    return provider_name.capitalize()


class EnterpriseRAG:
    """Coordinates routing, RBAC, retrieval, and answer generation."""

    def __init__(
        self,
        vector_store: FaissVectorStore | None = None,
        data_dir: str | Path = DEFAULT_DATA_DIR,
        *,
        llm_provider: LLMProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_fallback_enabled: bool = True,
        metadata_retriever: MetadataAwareRetriever | None = None,
        metadata_settings: MetadataRetrievalSettings | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        hybrid_settings: HybridRetrievalSettings | None = None,
        reranker: CrossEncoderReranker | None = None,
        reranking_settings: RerankingSettings | None = None,
        query_processor: QueryProcessor | None = None,
        query_processing_settings: QueryProcessingSettings | None = None,
    ):
        self._vector_store = vector_store
        self.data_dir = Path(data_dir)
        self._retriever: SemanticRetriever | None = None
        self._llm_provider = llm_provider
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_fallback_enabled = llm_fallback_enabled
        self._hybrid_settings = hybrid_settings or HybridRetrievalSettings.from_settings()
        self._reranking_settings = reranking_settings or RerankingSettings.from_settings()
        self._query_processing_settings = (
            query_processing_settings or QueryProcessingSettings.from_settings()
        )
        self._metadata_settings = metadata_settings or MetadataRetrievalSettings.from_settings()
        self._metadata_retriever = metadata_retriever or MetadataAwareRetriever(
            settings=self._metadata_settings,
        )
        self._hybrid_retriever = hybrid_retriever or HybridRetriever(
            settings=self._hybrid_settings,
            metadata_retriever=self._metadata_retriever,
        )
        self._reranker = reranker or CrossEncoderReranker(settings=self._reranking_settings)
        self._query_processor = query_processor or QueryProcessor(
            settings=self._query_processing_settings,
            hybrid_settings=self._hybrid_settings,
            metadata_settings=self._metadata_settings,
            reranking_settings=self._reranking_settings,
        )
        self._standalone_bm25: BM25Index | None = None
        self.answer_generator = AnswerGenerator()
        self._initialized = False

    @property
    def retriever(self) -> SemanticRetriever:
        """Legacy fixture retriever — created only when needed."""
        if self._retriever is None:
            self._retriever = SemanticRetriever()
        return self._retriever

    @property
    def vector_store(self) -> FaissVectorStore | None:
        return self._vector_store

    def _resolve_faiss_store(self):
        if isinstance(self._vector_store, HybridIndexStore):
            return self._vector_store.faiss_store
        return self._vector_store

    def _resolve_bm25_index(self) -> BM25Index:
        if isinstance(self._vector_store, HybridIndexStore):
            return self._vector_store.bm25_index
        if self._standalone_bm25 is None:
            from app.config import get_settings

            settings = get_settings()
            persist_path = settings.indexes_path / "bm25_corpus.json"
            self._standalone_bm25 = BM25Index(
                settings=self._hybrid_settings,
                persist_path=persist_path,
            )
            self._standalone_bm25.load()
        return self._standalone_bm25

    def initialize(self) -> int:
        """Prepare retrieval — shared vector store or legacy fixture index."""
        if self._vector_store is not None:
            faiss_store = self._resolve_faiss_store()
            if self._hybrid_settings.enabled:
                self._hybrid_retriever.ensure_bm25_synced(
                    faiss_store,
                    self._resolve_bm25_index(),
                )
            if self._reranking_settings.enabled:
                self._reranker.preload()
            self._initialized = True
            log_with_fields(
                logger,
                logging.INFO,
                "RAG engine initialized from shared vector store",
                vector_count=faiss_store.size,
                embedding_model=faiss_store.model_name,
                embedding_dimension=faiss_store.dimension,
                hybrid_enabled=self._hybrid_settings.enabled,
                reranking_enabled=self._reranking_settings.enabled,
                rerank_model=self._reranking_settings.rerank_model_id,
                query_intelligence_enabled=self._query_processing_settings.enabled,
                bm25_count=self._resolve_bm25_index().size,
            )
            return faiss_store.size

        chunks = load_documents(self.data_dir)
        self.retriever.build_index(chunks)
        self._initialized = True
        log_with_fields(
            logger,
            logging.INFO,
            "RAG engine initialized from fixture documents",
            data_dir=str(self.data_dir),
            chunk_count=len(chunks),
        )
        return len(chunks)

    def _search(
        self,
        user_query: str,
        *,
        top_k: int | None = None,
        allowed_categories: set[str],
        authorized_sources: frozenset[str] | None,
    ) -> list[RetrievalResult]:
        if self._vector_store is not None:
            faiss_store = self._resolve_faiss_store()
            if self._hybrid_settings.enabled:
                query_outcome = self._query_processor.process(user_query)
                context_top_k = _resolve_context_top_k(
                    query_outcome.classification.category,
                    explicit_top_k=top_k,
                )
                effective_hybrid_settings = apply_strategy_to_hybrid_settings(
                    self._hybrid_settings,
                    query_outcome.strategy,
                )
                effective_metadata_settings = apply_strategy_to_metadata_settings(
                    self._metadata_settings,
                    query_outcome.strategy,
                )
                effective_rerank_settings = apply_strategy_to_rerank_settings(
                    self._reranking_settings,
                    query_outcome.strategy,
                )
                fetch_k = (
                    effective_rerank_settings.rerank_top_n
                    if effective_rerank_settings.enabled
                    else context_top_k
                )
                if query_outcome.classification.category in (
                    QueryCategory.LIST,
                    QueryCategory.TABLE,
                ):
                    fetch_k = max(fetch_k, 30)

                strategy_retriever = HybridRetriever(
                    settings=effective_hybrid_settings,
                    metadata_retriever=MetadataAwareRetriever(
                        settings=effective_metadata_settings,
                    ),
                )
                # Empty frozenset must remain deny-all — never coerce to None
                # (None means "no source filter" / unrestricted retrieval).
                allowed_source_set = (
                    set(authorized_sources)
                    if authorized_sources is not None
                    else None
                )
                # Diagnostics only — never alters ranking or return values.
                try:
                    from app.rag.observability.collector import get_active_trace

                    _trace = get_active_trace()
                except Exception:  # noqa: BLE001
                    _trace = None
                if _trace is not None:
                    _trace.set_understanding(
                        {
                            "intent": getattr(
                                query_outcome, "understanding_intent", None
                            )
                            or query_outcome.classification.category.value,
                            "entities": list(query_outcome.detected_entities or ()),
                            "concepts": list(
                                getattr(query_outcome, "understanding_concepts", ())
                                or ()
                            ),
                            "likely_documents": list(
                                getattr(
                                    query_outcome,
                                    "understanding_likely_documents",
                                    (),
                                )
                                or ()
                            ),
                        }
                    )
                    _trace.set_expansion(
                        list(query_outcome.retrieval_queries),
                        strategy=getattr(
                            query_outcome, "expansion_strategy", None
                        ),
                    )

                per_query_results: list[list[RetrievalResult]] = []
                for retrieval_query in query_outcome.retrieval_queries:
                    if _trace is not None:
                        _trace.begin_retrieval_query(retrieval_query)
                    query_hits = strategy_retriever.search(
                        faiss_store,
                        self._resolve_bm25_index(),
                        retrieval_query,
                        top_k=fetch_k,
                        allowed_categories=allowed_categories,
                        allowed_sources=allowed_source_set,
                    )
                    if _trace is not None:
                        _trace.record_per_query_metadata_results(query_hits)
                    per_query_results.append(query_hits)

                candidates = merge_multi_query_results(
                    per_query_results,
                    limit=fetch_k,
                )
                if _trace is not None:
                    _trace.record_merge(candidates)
                effective_reranker = CrossEncoderReranker(
                    settings=effective_rerank_settings,
                    runtime=self._reranker.runtime,
                    metadata_bonus_reference=effective_metadata_settings.max_metadata_bonus,
                )
                reranked = effective_reranker.rerank(
                    user_query,
                    candidates,
                    top_k=context_top_k,
                )
                if _trace is not None:
                    _trace.record_rerank(reranked)
                focus_source_chunks = None
                if query_outcome.classification.category in (
                    QueryCategory.LIST,
                    QueryCategory.TABLE,
                ) and reranked:
                    source_scores: dict[str, float] = {}
                    for item in reranked[:10]:
                        score = (
                            item.reranker_score
                            if item.reranker_score is not None
                            else item.confidence
                        )
                        source_scores[item.source] = (
                            source_scores.get(item.source, 0.0) + score
                        )
                    focus_source = max(source_scores, key=source_scores.get)
                    focus_source_chunks = _collect_focus_document_chunks(
                        faiss_store,
                        focus_source,
                        candidates,
                    )
                final_results = _expand_exhaustive_context(
                    reranked,
                    candidates,
                    top_k=context_top_k,
                    category=query_outcome.classification.category,
                    focus_source_chunks=focus_source_chunks,
                    query=user_query,
                )
                if _trace is not None:
                    _trace.record_final_context(final_results)
                    try:
                        _trace.evaluate_expected(list(faiss_store.chunks))
                    except Exception:  # noqa: BLE001
                        pass
                _log_retrieval_pipeline_debug(
                    query=user_query,
                    category=query_outcome.classification.category.value,
                    context_top_k=context_top_k,
                    candidates=candidates,
                    final_results=final_results,
                )
                return self._annotate_query_processing(final_results, query_outcome)
            resolved_top_k = top_k if top_k is not None else get_settings().top_k_final
            return self._metadata_retriever.search_vector_store(
                faiss_store,
                user_query,
                top_k=resolved_top_k,
                allowed_categories=allowed_categories,
                allowed_sources=(
                    set(authorized_sources)
                    if authorized_sources is not None
                    else None
                ),
            )

        resolved_top_k = top_k if top_k is not None else get_settings().top_k_final
        return self._metadata_retriever.search_semantic_retriever(
            self.retriever,
            user_query,
            top_k=resolved_top_k,
            allowed_categories=allowed_categories,
            allowed_sources=(
                set(authorized_sources)
                if authorized_sources is not None
                else None
            ),
        )

    @staticmethod
    def _annotate_query_processing(
        results: list[RetrievalResult],
        outcome,
    ) -> list[RetrievalResult]:
        """Attach query intelligence explainability to retrieval hits."""
        if not results:
            return results

        from dataclasses import replace

        explanation = [
            f"Original Query: {outcome.original_query}",
            f"Expanded Query: {outcome.expanded_query}",
            f"Detected Intent: {getattr(outcome, 'understanding_intent', None) or outcome.classification.category.value}",
            f"Classification: {outcome.classification.category.value}",
            f"Retrieval Strategy: {outcome.strategy.name}",
            f"Expansion Strategy: {getattr(outcome, 'expansion_strategy', None) or 'n/a'}",
            f"Sparse Weight: {outcome.strategy.sparse_weight}",
            f"Dense Weight: {outcome.strategy.dense_weight}",
            f"Metadata Bonus Multiplier: {outcome.strategy.metadata_bonus_multiplier}",
            f"Generated Queries: {len(outcome.retrieval_queries)}",
            f"Retrieval Queries: {' | '.join(outcome.retrieval_queries)}",
        ]
        concepts = getattr(outcome, "understanding_concepts", ()) or ()
        if concepts:
            explanation.append(f"Detected Concepts: {', '.join(concepts)}")
        likely_docs = getattr(outcome, "understanding_likely_documents", ()) or ()
        if likely_docs:
            explanation.append(f"Likely Documents: {', '.join(likely_docs)}")
        if outcome.detected_entities:
            explanation.append(
                f"Detected Entities: {', '.join(outcome.detected_entities)}"
            )

        annotated: list[RetrievalResult] = []
        for result in results:
            merged_explanation = list(result.score_explanation or []) + explanation
            annotated.append(
                replace(
                    result,
                    detected_intent=outcome.classification.category.value,
                    score_explanation=merged_explanation,
                )
            )
        return annotated

    def _generate_answer(
        self,
        user_query: str,
        results: list[RetrievalResult],
        *,
        conversation_history: str | None = None,
    ) -> GenerationOutcome:
        """Generate an answer via LLM when configured, else rule-based fallback."""
        sources_used = _collect_sources(results)
        retrieval_confidence = results[0].confidence if results else 0.0
        used_llm_fallback = False

        answer_plan = None
        try:
            from app.answer_planning import plan_answer

            answer_plan = plan_answer(user_query)
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_answer_plan(answer_plan.to_dict())
        except Exception:  # noqa: BLE001
            answer_plan = None

        evidence_graph = None
        try:
            from app.evidence_organization import organize_evidence

            evidence_graph = organize_evidence(results, answer_plan=answer_plan)
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_evidence_graph(evidence_graph.to_dict())
        except Exception:  # noqa: BLE001
            evidence_graph = None

        answer_composition = None
        try:
            from app.evidence_composition import compose_answer_evidence

            answer_composition = compose_answer_evidence(
                evidence_graph,
                question=user_query,
                answer_plan=answer_plan,
            )
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_answer_composition(answer_composition.to_dict())
        except Exception:  # noqa: BLE001
            answer_composition = None

        # Phase 4F — synthesis plan (concept composition before prompt generation).
        answer_synthesis = None
        try:
            from app.answer_synthesis import plan_answer_synthesis

            answer_synthesis = plan_answer_synthesis(
                question=user_query,
                answer_plan=answer_plan,
                evidence_graph=evidence_graph,
                answer_composition=answer_composition,
            )
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_answer_synthesis(answer_synthesis.to_dict())
        except Exception:  # noqa: BLE001
            answer_synthesis = None

        if answer_synthesis is not None and answer_synthesis.is_unsupported:
            refusal = (
                answer_synthesis.refusal_message
                or "I couldn't find this information in the retrieved context."
            )
            log_with_fields(
                logger,
                logging.INFO,
                "Synthesis planner refused unsupported factual request",
                unsupported_concepts=list(answer_synthesis.unsupported_concepts),
            )
            try:
                from app.rag.observability.collector import get_active_trace

                _trace = get_active_trace()
                if _trace is not None:
                    _trace.record_model_output(refusal)
            except Exception:  # noqa: BLE001
                pass
            layout_payload = None
            rendered = refusal
            try:
                from app.response_experience import (
                    finalize_enterprise_markdown,
                    plan_response_experience,
                    polish_enterprise_markdown,
                    render_enterprise_markdown,
                )

                layout = plan_response_experience(
                    question=user_query,
                    answer=refusal,
                    answer_plan=answer_plan,
                    evidence_graph=evidence_graph,
                    answer_synthesis=answer_synthesis,
                )
                render_result = render_enterprise_markdown(
                    layout=layout,
                    answer=refusal,
                    question=user_query,
                    sources=list(sources_used),
                )
                polish_result = polish_enterprise_markdown(render_result.markdown)
                finalize_result = finalize_enterprise_markdown(polish_result.markdown)
                rendered = finalize_result.markdown
                layout_payload = layout.to_dict()
                layout_payload["render"] = render_result.to_dict()
                layout_payload["polish"] = polish_result.to_dict()
                layout_payload["finalize"] = finalize_result.to_dict()
                from app.rag.observability.collector import get_active_trace

                _trace = get_active_trace()
                if _trace is not None:
                    _trace.record_response_layout(layout_payload)
                    _trace.record_markdown_render(render_result.to_dict())
                    _trace.record_presentation_polish(polish_result.to_dict())
                    _trace.record_presentation_finalize(finalize_result.to_dict())
            except Exception:  # noqa: BLE001
                layout_payload = None
            return GenerationOutcome(
                answer=rendered,
                sources_used=sources_used,
                retrieval_confidence=0.05,
                generation_backend="synthesis_unsupported",
                response_layout=layout_payload,
            )

        outcome: GenerationOutcome | None = None
        if self._llm_provider is not None:
            provider_label = _provider_display_name(self._llm_provider.provider_name)
            model_label = self._llm_provider.model_name
            try:
                prompt = self._prompt_builder.build(
                    user_query,
                    results,
                    conversation_history=conversation_history,
                    answer_plan=answer_plan,
                    evidence_graph=evidence_graph,
                    answer_composition=answer_composition,
                    answer_synthesis=answer_synthesis,
                )
                request = LLMGenerationRequest(
                    question=user_query,
                    retrieved_chunks=results,
                    conversation_history=conversation_history,
                    prompt=prompt,
                )
                llm_result = self._llm_provider.generate_sync(request)
                try:
                    from app.rag.observability.collector import get_active_trace

                    _trace = get_active_trace()
                    if _trace is not None:
                        _trace.record_model_output(llm_result.answer)
                except Exception:  # noqa: BLE001
                    pass
                log_with_fields(
                    logger,
                    logging.INFO,
                    "✓ LLM response generated successfully",
                    provider=provider_label,
                    model=model_label,
                )
                outcome = GenerationOutcome(
                    answer=llm_result.answer,
                    sources_used=sources_used,
                    retrieval_confidence=retrieval_confidence,
                    generation_backend="llm",
                    provider_name=llm_result.provider_name,
                    model=llm_result.model,
                    latency_ms=llm_result.latency_ms,
                    token_usage=llm_result.token_usage,
                    prompt_length=prompt.total_length,
                )
            except LLMError as exc:
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "❌ LLM request failed",
                    provider=provider_label,
                    model=model_label,
                    reason=str(exc),
                )
                if not self._llm_fallback_enabled:
                    log_with_fields(
                        logger,
                        logging.WARNING,
                        "Fallback disabled. Returning LLM error.",
                        provider=provider_label,
                        model=model_label,
                    )
                    raise
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "⚠ Falling back to AnswerGenerator",
                    provider=provider_label,
                    model=model_label,
                )
                used_llm_fallback = True

        if outcome is None:
            generated = self.answer_generator.generate(user_query, results)
            try:
                from app.rag.observability.collector import get_active_trace

                _trace = get_active_trace()
                if _trace is not None:
                    _trace.record_model_output(generated.answer)
            except Exception:  # noqa: BLE001
                pass
            if used_llm_fallback:
                log_with_fields(
                    logger,
                    logging.INFO,
                    "✓ AnswerGenerator fallback completed successfully",
                )
            outcome = GenerationOutcome(
                answer=generated.answer,
                sources_used=generated.sources_used,
                retrieval_confidence=generated.confidence_score,
                generation_backend="answer_generator",
            )

        # Phase 4D/4E — GAQA: validate, calibrate confidence, apply reliability overrides.
        try:
            from app.gaqa import run_gaqa

            gaqa_report = run_gaqa(
                question=user_query,
                answer=outcome.answer,
                results=results,
                answer_plan=answer_plan,
                evidence_graph=evidence_graph,
                answer_composition=answer_composition,
            )
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_gaqa_report(gaqa_report.to_dict())
            from dataclasses import replace

            final_answer = outcome.answer
            if gaqa_report.recommended_final_answer:
                final_answer = gaqa_report.recommended_final_answer
            outcome = replace(
                outcome,
                answer=final_answer,
                retrieval_confidence=round(float(gaqa_report.overall_confidence), 4),
            )
            log_with_fields(
                logger,
                logging.INFO,
                "GAQA validation completed",
                confidence_label=gaqa_report.confidence_label,
                overall_confidence=round(gaqa_report.overall_confidence, 4),
                answer_completeness=gaqa_report.answer_completeness,
                intent_coverage=round(gaqa_report.intent_coverage, 4),
                reliability_score=round(gaqa_report.overall_reliability_score, 4),
                refusal_reason=gaqa_report.refusal_reason,
                missing_concepts=list(gaqa_report.missing_concepts),
                unsupported_claims=gaqa_report.unsupported_claim_count,
                answer_overridden=bool(gaqa_report.recommended_final_answer),
            )
        except Exception:  # noqa: BLE001
            pass

        # Phase 5A/5B — Response Experience layout + Enterprise Markdown render.
        try:
            from app.response_experience import (
                finalize_enterprise_markdown,
                plan_response_experience,
                polish_enterprise_markdown,
                render_enterprise_markdown,
            )
            from dataclasses import replace

            layout = plan_response_experience(
                question=user_query,
                answer=outcome.answer,
                answer_plan=answer_plan,
                evidence_graph=evidence_graph,
                answer_synthesis=answer_synthesis,
            )
            related_docs: list[str] = []
            if answer_synthesis is not None:
                related_docs = list(answer_synthesis.supporting_documents or [])
            render_result = render_enterprise_markdown(
                layout=layout,
                answer=outcome.answer,
                question=user_query,
                sources=list(outcome.sources_used or []),
                related_documents=related_docs,
            )
            polish_result = polish_enterprise_markdown(render_result.markdown)
            finalize_result = finalize_enterprise_markdown(polish_result.markdown)
            layout_payload = layout.to_dict()
            layout_payload["render"] = render_result.to_dict()
            layout_payload["polish"] = polish_result.to_dict()
            layout_payload["finalize"] = finalize_result.to_dict()
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_response_layout(layout_payload)
                _trace.record_markdown_render(render_result.to_dict())
                _trace.record_presentation_polish(polish_result.to_dict())
                _trace.record_presentation_finalize(finalize_result.to_dict())
            outcome = replace(
                outcome,
                answer=finalize_result.markdown,
                response_layout=layout_payload,
            )
            log_with_fields(
                logger,
                logging.INFO,
                "RX Engine layout selected, markdown rendered, polished, and finalized",
                response_layout=layout.layout.value,
                expected_render_type=layout.expected_render_type,
                markdown_template=render_result.template_used,
                components_rendered=render_result.components_rendered,
                components_skipped=render_result.components_skipped,
                polish_transforms=polish_result.transforms_applied,
                finalize_transforms=finalize_result.transforms_applied,
            )
        except Exception:  # noqa: BLE001
            pass

        return outcome

    def query(
        self,
        user_query: str,
        role: str,
        authorized_sources: frozenset[str] | None = None,
        *,
        conversation_history: str | None = None,
    ) -> QueryResponse:
        """Process a query with routing and RBAC enforcement."""
        if not self._initialized:
            raise RuntimeError("RAG pipeline not initialized. Call initialize() first.")

        normalized_role = validate_role(role)
        route = route_query(user_query)

        access = check_access(normalized_role, route.category)
        if not access.allowed:
            return QueryResponse(
                query=user_query,
                role=normalized_role,
                routed_category=route.category,
                route_confidence=route.confidence,
                answer="",
                sources_used=[],
                citations=[],
                confidence_score=0.0,
                access_granted=False,
                message=access.message,
            )

        allowed_categories = set(get_accessible_categories(normalized_role))
        context_top_k = _resolve_context_top_k(None)
        log_with_fields(
            logger,
            logging.INFO,
            "RAG retrieval started",
            query=user_query,
            role=normalized_role,
            routed_category=route.category,
            allowed_categories=sorted(allowed_categories),
            authorized_source_count=(
                len(authorized_sources) if authorized_sources is not None else None
            ),
            top_k=context_top_k,
            retrieval_backend=(
                "shared_vector_store"
                if self._vector_store is not None
                else "legacy_fixture_index"
            ),
            has_conversation_history=bool(conversation_history),
        )

        results = self._search(
            user_query,
            allowed_categories=allowed_categories,
            authorized_sources=authorized_sources,
        )

        if not results:
            log_with_fields(
                logger,
                logging.WARNING,
                "RAG retrieval returned no chunks",
                query=user_query,
                role=normalized_role,
                allowed_categories=sorted(allowed_categories),
                authorized_source_count=(
                    len(authorized_sources) if authorized_sources is not None else None
                ),
            )
            try:
                from app.query_router.routing_debug import log_rag_retrieval_stage

                log_rag_retrieval_stage(
                    question=user_query,
                    chunk_count=0,
                    top_documents=[],
                    prompt_context_chars=0,
                    response_type="document_insufficient",
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                from app.rag.observability.collector import get_active_trace

                _trace = get_active_trace()
                if _trace is not None:
                    _trace.record_final_answer(
                        INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE,
                        answer_kind="document_insufficient",
                    )
            except Exception:  # noqa: BLE001
                pass
            return QueryResponse(
                query=user_query,
                role=normalized_role,
                routed_category=route.category,
                route_confidence=route.confidence,
                answer=INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE,
                sources_used=[],
                citations=[],
                confidence_score=0.0,
                access_granted=True,
                message="Search completed but no matching chunks were found.",
            )

        generated = self._generate_answer(
            user_query,
            results,
            conversation_history=conversation_history,
        )
        citations = _build_citations(results)
        sources_label = ", ".join(generated.sources_used)

        log_with_fields(
            logger,
            logging.INFO,
            "RAG context assembled",
            query=user_query,
            chunks_used=len(results),
            chunk_ids=[item.chunk_id for item in results],
            chunk_sources=[item.source for item in results],
            chunk_confidences=[item.confidence for item in results],
            prompt_sources=generated.sources_used,
            retrieval_confidence=generated.retrieval_confidence,
            generation_backend=generated.generation_backend,
            provider=generated.provider_name,
            model=generated.model,
        )
        try:
            from app.query_router.routing_debug import log_rag_retrieval_stage

            top_docs = [
                {
                    "source": item.source,
                    "chunk_id": item.chunk_id,
                    "score": round(float(item.confidence), 4),
                    "page": item.page_number,
                }
                for item in results[:8]
            ]
            prompt_chars = sum(len(item.content or "") for item in results)
            log_rag_retrieval_stage(
                question=user_query,
                chunk_count=len(results),
                top_documents=top_docs,
                prompt_context_chars=prompt_chars,
                response_type=generated.generation_backend,
            )
        except Exception:  # noqa: BLE001
            pass

        try:
            from app.rag.observability.collector import get_active_trace

            _trace = get_active_trace()
            if _trace is not None:
                _trace.record_final_answer(
                    generated.answer,
                    answer_kind=generated.generation_backend,
                )
        except Exception:  # noqa: BLE001
            pass

        return QueryResponse(
            query=user_query,
            role=normalized_role,
            routed_category=route.category,
            route_confidence=route.confidence,
            answer=generated.answer,
            sources_used=generated.sources_used,
            citations=citations,
            confidence_score=generated.retrieval_confidence,
            access_granted=True,
            message=f"Answer generated from {sources_label}.",
            response_layout=generated.response_layout,
        )
