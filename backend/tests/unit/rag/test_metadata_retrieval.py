"""Unit tests for Phase 12.5 metadata-aware retrieval."""

from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.types import ChunkMetadata, ChunkType
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.metadata_retrieval.intent import QueryIntent, detect_query_intent
from app.rag.metadata_retrieval.retriever import MetadataAwareRetriever
from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.rag.metadata_retrieval.scorer import score_candidate
from app.rag.types import calibrate_confidence


def _chunk(
    *,
    chunk_id: str,
    content: str,
    metadata: ChunkMetadata | None = None,
    source: str = "doc.pdf",
) -> DocumentChunk:
    page = metadata.page_start if metadata is not None else None
    return DocumentChunk(
        chunk_id=chunk_id,
        content=content,
        source=source,
        category="general",
        chunk_index=0,
        page_number=page,
        metadata=metadata,
    )


def _metadata(
    *,
    chunk_type: ChunkType,
    section_title: str | None = None,
    reading_order: int = 0,
    contains_table: bool = False,
    contains_list: bool = False,
    hierarchy_path: tuple[str, ...] = (),
) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_type=chunk_type,
        section_title=section_title,
        reading_order=reading_order,
        contains_table=contains_table,
        contains_list=contains_list,
        hierarchy_path=hierarchy_path,
    )


class TestIntentDetection:
    def test_entity_lookup(self):
        result = detect_query_intent("What is the headquarters location?")
        assert result.primary == QueryIntent.ENTITY_LOOKUP

    def test_section_lookup(self):
        result = detect_query_intent("What are the strategic priorities in section 7?")
        assert result.primary == QueryIntent.SECTION_LOOKUP

    def test_list_intent(self):
        result = detect_query_intent("List the remote work requirements")
        assert result.primary == QueryIntent.LIST_INTENT

    def test_table_intent(self):
        result = detect_query_intent("Show the revenue breakdown table")
        assert result.primary == QueryIntent.TABLE_INTENT

    def test_numeric_intent(self):
        result = detect_query_intent("How many employees are in Singapore?")
        assert result.primary == QueryIntent.NUMERIC_INTENT


class TestMetadataScoring:
    def test_heading_similarity_boosts_matching_section(self):
        settings = MetadataRetrievalSettings(section_title_similarity_weight=0.10)
        candidate = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="c1",
                content="Singapore is the group headquarters.",
                metadata=_metadata(
                    chunk_type=ChunkType.PARAGRAPH,
                    section_title="Geographic Presence",
                ),
            ),
            raw_cosine_score=0.50,
        )
        breakdown = score_candidate(
            "Geographic presence headquarters",
            candidate,
            intent_result=detect_query_intent("Geographic presence headquarters"),
            settings=settings,
            peers=[candidate],
            calibrated_cosine=calibrate_confidence(0.50),
        )
        assert breakdown.metadata_bonus > 0
        assert any("similarity" in item.lower() for item in breakdown.explanations)

    def test_table_intent_prefers_table_chunks(self):
        settings = MetadataRetrievalSettings(table_intent_boost=0.08)
        table_candidate = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="table-1",
                content="Revenue | FY2026",
                metadata=_metadata(
                    chunk_type=ChunkType.TABLE,
                    section_title="Financial Summary",
                    contains_table=True,
                ),
            ),
            raw_cosine_score=0.55,
        )
        paragraph_candidate = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="para-1",
                content="Revenue grew steadily.",
                metadata=_metadata(
                    chunk_type=ChunkType.PARAGRAPH,
                    section_title="Financial Summary",
                ),
            ),
            raw_cosine_score=0.55,
        )
        table_breakdown = score_candidate(
            "Show the revenue table",
            table_candidate,
            intent_result=detect_query_intent("Show the revenue table"),
            settings=settings,
            peers=[table_candidate, paragraph_candidate],
            calibrated_cosine=calibrate_confidence(0.55),
        )
        paragraph_breakdown = score_candidate(
            "Show the revenue table",
            paragraph_candidate,
            intent_result=detect_query_intent("Show the revenue table"),
            settings=settings,
            peers=[table_candidate, paragraph_candidate],
            calibrated_cosine=calibrate_confidence(0.55),
        )
        assert table_breakdown.final_score > paragraph_breakdown.final_score
        assert any("Table intent" in item for item in table_breakdown.explanations)

    def test_entity_lookup_prefers_paragraph_chunks(self):
        settings = MetadataRetrievalSettings(paragraph_intent_boost=0.08)
        paragraph_candidate = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="para-1",
                content="GTFS headquarters is in Singapore.",
                metadata=_metadata(chunk_type=ChunkType.PARAGRAPH),
            ),
            raw_cosine_score=0.52,
        )
        table_candidate = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="table-1",
                content="Office | Country",
                metadata=_metadata(chunk_type=ChunkType.TABLE, contains_table=True),
            ),
            raw_cosine_score=0.52,
        )
        paragraph_breakdown = score_candidate(
            "What is the headquarters?",
            paragraph_candidate,
            intent_result=detect_query_intent("What is the headquarters?"),
            settings=settings,
            peers=[paragraph_candidate, table_candidate],
            calibrated_cosine=calibrate_confidence(0.52),
        )
        table_breakdown = score_candidate(
            "What is the headquarters?",
            table_candidate,
            intent_result=detect_query_intent("What is the headquarters?"),
            settings=settings,
            peers=[paragraph_candidate, table_candidate],
            calibrated_cosine=calibrate_confidence(0.52),
        )
        assert paragraph_breakdown.final_score > table_breakdown.final_score

    def test_section_continuity_bonus(self):
        settings = MetadataRetrievalSettings(section_continuity_weight=0.06)
        first = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="c1",
                content="Leave policy details",
                metadata=_metadata(
                    chunk_type=ChunkType.PARAGRAPH,
                    section_title="Leave Policy",
                    reading_order=1,
                ),
            ),
            raw_cosine_score=0.60,
        )
        second = VectorSearchCandidate(
            chunk=_chunk(
                chunk_id="c2",
                content="Annual leave entitlement",
                metadata=_metadata(
                    chunk_type=ChunkType.PARAGRAPH,
                    section_title="Leave Policy",
                    reading_order=2,
                ),
            ),
            raw_cosine_score=0.58,
        )
        breakdown = score_candidate(
            "annual leave policy",
            second,
            intent_result=detect_query_intent("annual leave policy"),
            settings=settings,
            peers=[first, second],
            calibrated_cosine=calibrate_confidence(0.58),
        )
        assert any("Section continuity" in item for item in breakdown.explanations)


class TestMetadataAwareRetriever:
    def test_rescore_and_rank_is_deterministic(self):
        settings = MetadataRetrievalSettings(
            paragraph_intent_boost=0.08,
            table_intent_boost=0.02,
        )
        retriever = MetadataAwareRetriever(settings=settings)
        candidates = [
            VectorSearchCandidate(
                chunk=_chunk(
                    chunk_id="b",
                    content="Table row",
                    metadata=_metadata(chunk_type=ChunkType.TABLE, contains_table=True),
                ),
                raw_cosine_score=0.62,
            ),
            VectorSearchCandidate(
                chunk=_chunk(
                    chunk_id="a",
                    content="Paragraph answer",
                    metadata=_metadata(
                        chunk_type=ChunkType.PARAGRAPH,
                        section_title="Headquarters",
                    ),
                ),
                raw_cosine_score=0.60,
            ),
        ]
        first = retriever._rescore_and_rank(
            "What is the headquarters?",
            candidates,
            top_k=2,
        )
        second = retriever._rescore_and_rank(
            "What is the headquarters?",
            candidates,
            top_k=2,
        )
        assert [item.chunk_id for item in first] == [item.chunk_id for item in second]

    def test_tie_breaking_uses_chunk_id(self):
        retriever = MetadataAwareRetriever(
            settings=MetadataRetrievalSettings(max_metadata_bonus=0.0)
        )
        candidates = [
            VectorSearchCandidate(
                chunk=_chunk(chunk_id="z-chunk", content="Zulu"),
                raw_cosine_score=0.70,
            ),
            VectorSearchCandidate(
                chunk=_chunk(chunk_id="a-chunk", content="Alpha"),
                raw_cosine_score=0.70,
            ),
        ]
        results = retriever._rescore_and_rank("general query", candidates, top_k=2)
        assert results[0].chunk_id == "a-chunk"

    def test_explainability_fields_populated(self):
        retriever = MetadataAwareRetriever()
        candidates = [
            VectorSearchCandidate(
                chunk=_chunk(
                    chunk_id="c1",
                    content="Strategic priorities for FY2026",
                    metadata=_metadata(
                        chunk_type=ChunkType.SECTION_HEADER,
                        section_title="Strategic Priorities",
                    ),
                ),
                raw_cosine_score=0.63,
            )
        ]
        results = retriever._rescore_and_rank(
            "What are the strategic priorities?",
            candidates,
            top_k=1,
        )
        result = results[0]
        assert result.raw_cosine_score == 0.63
        assert result.metadata_bonus is not None
        assert result.final_score is not None
        assert result.final_score >= result.confidence
        assert result.score_explanation
        assert result.detected_intent == QueryIntent.SECTION_LOOKUP.value
        assert result.chunk_type == ChunkType.SECTION_HEADER.value

    def test_metadata_bonus_capped(self):
        settings = MetadataRetrievalSettings(
            max_metadata_bonus=0.05,
            section_title_similarity_weight=0.20,
            paragraph_intent_boost=0.20,
        )
        retriever = MetadataAwareRetriever(settings=settings)
        candidates = [
            VectorSearchCandidate(
                chunk=_chunk(
                    chunk_id="c1",
                    content="Strategic priorities section",
                    metadata=_metadata(
                        chunk_type=ChunkType.PARAGRAPH,
                        section_title="Strategic Priorities",
                    ),
                ),
                raw_cosine_score=0.40,
            )
        ]
        results = retriever._rescore_and_rank(
            "What are the strategic priorities?",
            candidates,
            top_k=1,
        )
        assert results[0].metadata_bonus <= 0.05
