"""Unit tests for AI-powered suggested question generation."""

from __future__ import annotations

from app.documents.events import (
    DocumentDeleted,
    DocumentIndexed,
    DocumentProcessingStarted,
    DocumentReindexed,
    DocumentUploaded,
)
from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.types import ChunkMetadata, ChunkType
from app.llm.types import LLMGenerationResult
from app.services.suggested_questions import (
    ONBOARDING_QUESTIONS_BASE,
    ONBOARDING_UPLOAD_QUESTION,
    SuggestedQuestion,
    SuggestedQuestionService,
    _build_pool,
    _collect_document_profiles,
    _diversify,
    _extract_chunks,
    _heading_to_question,
    _parse_llm_question_lines,
)


def _chunk(
    source: str,
    content: str,
    *,
    section_title: str | None = None,
    document_title: str | None = None,
    chunk_index: int = 0,
) -> DocumentChunk:
    metadata = ChunkMetadata(
        chunk_type=ChunkType.PARAGRAPH,
        section_title=section_title,
        document_title=document_title,
    )
    return DocumentChunk(
        chunk_id=f"{source}::{chunk_index}",
        content=content,
        source=source,
        category="general",
        chunk_index=chunk_index,
        metadata=metadata,
    )


class _StubLLMProvider:
    """Minimal ``LLMProvider``-shaped stub for suggested-question tests."""

    def __init__(self, *, answer: str | None = None, raises: Exception | None = None) -> None:
        self._answer = answer
        self._raises = raises
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def model_name(self) -> str:
        return "stub-model"

    def generate_sync(self, request) -> LLMGenerationResult:  # noqa: ANN001
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return LLMGenerationResult(
            answer=self._answer or "",
            provider_name="stub",
            model="stub-model",
            latency_ms=1.0,
        )


class TestExtractChunks:
    def test_returns_chunks_from_plain_vector_store(self) -> None:
        class _PlainStore:
            chunks = [_chunk("a.pdf", "content")]

        assert _extract_chunks(_PlainStore()) == _PlainStore.chunks

    def test_returns_chunks_from_hybrid_store_via_faiss_store(self) -> None:
        class _Faiss:
            chunks = [_chunk("a.pdf", "content")]

        class _Hybrid:
            faiss_store = _Faiss()

        assert _extract_chunks(_Hybrid()) == _Hybrid.faiss_store.chunks

    def test_returns_empty_list_when_store_has_no_chunks_attribute(self) -> None:
        assert _extract_chunks(object()) == []


class TestCollectDocumentProfiles:
    def test_groups_headings_by_source_and_dedupes(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body 1",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Market Report",
            ),
            _chunk(
                "issuers.pdf",
                "body 2",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Market Report",
            ),
            _chunk(
                "issuers.pdf",
                "body 3",
                section_title="Investor Base",
                document_title="Commercial Paper Market Report",
            ),
        ]

        profiles = _collect_document_profiles(chunks)

        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.source == "issuers.pdf"
        assert profile.document_title == "Commercial Paper Market Report"
        assert profile.headings == ["Who are the main issuers?", "Investor Base"]

    def test_skips_generic_structural_headings(self) -> None:
        chunks = [
            _chunk("doc.pdf", "body", section_title="Introduction", document_title="Doc"),
            _chunk("doc.pdf", "body", section_title="Table of Contents", document_title="Doc"),
            _chunk("doc.pdf", "body", section_title="Remote Work Policy", document_title="Doc"),
        ]

        profiles = _collect_document_profiles(chunks)

        assert len(profiles) == 1
        assert profiles[0].headings == ["Remote Work Policy"]

    def test_skips_documents_with_no_usable_headings(self) -> None:
        chunks = [_chunk("empty.pdf", "body", section_title=None, document_title="Empty Doc")]

        assert _collect_document_profiles(chunks) == []

    def test_caps_headings_per_document(self) -> None:
        chunks = [
            _chunk(
                "doc.pdf",
                "body",
                section_title=f"Section Heading Number {i}",
                document_title="Doc",
                chunk_index=i,
            )
            for i in range(10)
        ]

        profiles = _collect_document_profiles(chunks, max_headings_per_document=3)

        assert len(profiles[0].headings) == 3

    def test_caps_document_count_keeping_most_recent(self) -> None:
        chunks = [
            _chunk(f"doc{i}.pdf", "body", section_title="Some Heading Text", document_title=f"Doc {i}")
            for i in range(5)
        ]

        profiles = _collect_document_profiles(chunks, max_documents=2)

        assert [p.source for p in profiles] == ["doc3.pdf", "doc4.pdf"]

    def test_ignores_short_and_overly_long_headings(self) -> None:
        chunks = [
            _chunk("doc.pdf", "body", section_title="FAQ", document_title="Doc", chunk_index=0),
            _chunk(
                "doc.pdf",
                "body",
                section_title=" ".join(["word"] * 20),
                document_title="Doc",
                chunk_index=1,
            ),
            _chunk("doc.pdf", "body", section_title="Valid Heading Text", document_title="Doc", chunk_index=2),
        ]

        profiles = _collect_document_profiles(chunks)

        assert profiles[0].headings == ["Valid Heading Text"]


class TestHeadingToQuestion:
    def test_interrogative_heading_is_used_verbatim(self) -> None:
        assert _heading_to_question("Who are the main issuers?", "Doc") == "Who are the main issuers?"

    def test_short_declarative_heading_uses_explain_template(self) -> None:
        result = _heading_to_question("Commercial Paper Market", "Doc")
        assert result == "Explain the commercial paper market."

    def test_heading_already_starting_with_article_is_not_doubled(self) -> None:
        result = _heading_to_question("The Repo Market", "Doc")
        assert result == "Explain the repo market."

    def test_long_declarative_heading_uses_document_context_template(self) -> None:
        heading = "Detailed Overview Of Investor Participation In The Market"
        result = _heading_to_question(heading, "Treasury Report")
        assert result.startswith("What does the Treasury Report document say about")

    def test_blank_heading_falls_back_to_generic_question(self) -> None:
        assert _heading_to_question("", "Doc") == "What does Doc cover?"


class TestParseLlmQuestionLines:
    def test_parses_valid_lines(self) -> None:
        raw = "1 | What are the main commercial paper issuers?\n2 | Explain the repo market."
        parsed = _parse_llm_question_lines(raw, num_documents=2, per_document=2)
        assert parsed[1] == ["What are the main commercial paper issuers?"]
        assert parsed[2] == ["Explain the repo market."]

    def test_ignores_malformed_lines(self) -> None:
        raw = "not a valid line\n1 | Explain the repo market."
        parsed = _parse_llm_question_lines(raw, num_documents=2, per_document=2)
        assert list(parsed.keys()) == [1]

    def test_ignores_out_of_range_index(self) -> None:
        raw = "5 | Explain the repo market."
        parsed = _parse_llm_question_lines(raw, num_documents=2, per_document=2)
        assert parsed == {}

    def test_ignores_too_short_or_too_long_questions(self) -> None:
        raw = "1 | Too short\n1 | " + " ".join(["word"] * 25)
        parsed = _parse_llm_question_lines(raw, num_documents=1, per_document=2)
        assert parsed == {}

    def test_respects_per_document_cap(self) -> None:
        raw = "\n".join([f"1 | Question number {i} about the market?" for i in range(5)])
        parsed = _parse_llm_question_lines(raw, num_documents=1, per_document=2)
        assert len(parsed[1]) == 2

    def test_strips_bullet_prefixes_and_quotes(self) -> None:
        raw = '- 1 | "Explain the repo market."'
        parsed = _parse_llm_question_lines(raw, num_documents=1, per_document=1)
        assert parsed[1] == ["Explain the repo market."]


class TestBuildPool:
    def test_returns_empty_pool_when_no_chunks(self) -> None:
        assert _build_pool([], None) == []

    def test_deterministic_fallback_without_llm_provider(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Report",
            ),
        ]

        pool = _build_pool(chunks, None)

        assert len(pool) == 1
        assert pool[0].text == "Who are the main issuers?"
        assert pool[0].source == "issuers.pdf"

    def test_uses_llm_output_when_available(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Report",
            ),
        ]
        provider = _StubLLMProvider(answer="1 | What are the main commercial paper issuers?")

        pool = _build_pool(chunks, provider)

        assert pool[0].text == "What are the main commercial paper issuers?"
        assert provider.calls == 1

    def test_falls_back_to_deterministic_when_llm_raises(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Report",
            ),
        ]
        provider = _StubLLMProvider(raises=RuntimeError("boom"))

        pool = _build_pool(chunks, provider)

        assert pool[0].text == "Who are the main issuers?"

    def test_partial_llm_response_falls_back_per_document(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body",
                section_title="Who are the main issuers?",
                document_title="Commercial Paper Report",
            ),
            _chunk(
                "handbook.pdf",
                "body",
                section_title="Remote Work Policy",
                document_title="Employee Handbook",
            ),
        ]
        # Only document 1 gets a usable LLM line; document 2 must fall back.
        provider = _StubLLMProvider(answer="1 | What are the main commercial paper issuers?")

        pool = _build_pool(chunks, provider)

        texts_by_source = {q.source: q.text for q in pool}
        assert texts_by_source["issuers.pdf"] == "What are the main commercial paper issuers?"
        assert texts_by_source["handbook.pdf"] == "Explain the remote work policy."


class TestDiversify:
    def test_prefers_one_question_per_source_first(self) -> None:
        pool = [
            SuggestedQuestion(text="a1", source="a.pdf", document_title="A"),
            SuggestedQuestion(text="a2", source="a.pdf", document_title="A"),
            SuggestedQuestion(text="b1", source="b.pdf", document_title="B"),
        ]

        result = _diversify(pool, limit=2)

        assert [q.text for q in result] == ["a1", "b1"]

    def test_fills_remainder_when_fewer_sources_than_limit(self) -> None:
        pool = [
            SuggestedQuestion(text="a1", source="a.pdf", document_title="A"),
            SuggestedQuestion(text="a2", source="a.pdf", document_title="A"),
        ]

        result = _diversify(pool, limit=2)

        assert [q.text for q in result] == ["a1", "a2"]


class TestSuggestedQuestionService:
    def test_caches_candidate_pool_across_calls(self) -> None:
        chunks = [
            _chunk(
                "issuers.pdf",
                "body",
                section_title="Who are the main issuers?",
                document_title="Doc",
            )
        ]

        class _Store:
            def __init__(self) -> None:
                self.calls = 0

            @property
            def chunks(self):
                self.calls += 1
                return chunks

        store = _Store()
        service = SuggestedQuestionService(store)

        service.get_candidate_pool()
        service.get_candidate_pool()

        assert store.calls == 1

    def test_invalidate_forces_rebuild(self) -> None:
        class _Store:
            def __init__(self) -> None:
                self.calls = 0
                self.chunks_value = []

            @property
            def chunks(self):
                self.calls += 1
                return self.chunks_value

        store = _Store()
        service = SuggestedQuestionService(store)

        service.get_candidate_pool()
        service.invalidate()
        service.get_candidate_pool()

        assert store.calls == 2

    def test_on_lifecycle_event_invalidates_for_indexed_and_deleted(self) -> None:
        class _Store:
            chunks: list = []

        service = SuggestedQuestionService(_Store())
        service._pool = []  # pretend the cache is already populated

        service.on_lifecycle_event(DocumentIndexed(document_id="1", user_id="u"))
        assert service._pool is None

        service._pool = []
        service.on_lifecycle_event(DocumentDeleted(document_id="1", user_id="u"))
        assert service._pool is None

        service._pool = []
        service.on_lifecycle_event(DocumentReindexed(document_id="1", user_id="u"))
        assert service._pool is None

    def test_on_lifecycle_event_ignores_unrelated_operations(self) -> None:
        class _Store:
            chunks: list = []

        service = SuggestedQuestionService(_Store())
        service._pool = []

        service.on_lifecycle_event(DocumentUploaded(document_id="1", user_id="u"))
        assert service._pool == []

        service.on_lifecycle_event(DocumentProcessingStarted(document_id="1", user_id="u"))
        assert service._pool == []

    def test_get_suggestions_filters_by_authorized_sources(self) -> None:
        sample_chunks = [
            _chunk("issuers.pdf", "body", section_title="Who are the main issuers?", document_title="Doc A"),
            _chunk("secret.pdf", "body", section_title="Confidential Roadmap Details", document_title="Doc B"),
        ]

        class _Store:
            chunks_value = sample_chunks

            @property
            def chunks(self):
                return self.chunks_value

        service = SuggestedQuestionService(_Store())

        suggestions = service.get_suggestions(frozenset({"issuers.pdf"}))

        assert all(question.source == "issuers.pdf" for question in suggestions)

    def test_get_suggestions_falls_back_to_onboarding_when_nothing_authorized(self) -> None:
        sample_chunks = [
            _chunk("issuers.pdf", "body", section_title="Who are the main issuers?", document_title="Doc A"),
        ]

        class _Store:
            chunks_value = sample_chunks

            @property
            def chunks(self):
                return self.chunks_value

        service = SuggestedQuestionService(_Store())

        suggestions = service.get_suggestions(frozenset())

        assert [q.text for q in suggestions] == list(ONBOARDING_QUESTIONS_BASE[:3])
        assert all(q.source == "" for q in suggestions)
        assert ONBOARDING_UPLOAD_QUESTION not in [q.text for q in suggestions]

    def test_get_suggestions_falls_back_to_onboarding_when_no_documents(self) -> None:
        class _Store:
            chunks: list = []

        service = SuggestedQuestionService(_Store())

        suggestions = service.get_suggestions(frozenset())

        assert [q.text for q in suggestions] == list(ONBOARDING_QUESTIONS_BASE[:3])

    def test_onboarding_includes_upload_prompt_when_can_upload(self) -> None:
        class _Store:
            chunks: list = []

        service = SuggestedQuestionService(_Store())
        suggestions = service.get_suggestions(frozenset(), can_upload=True)

        texts = [q.text for q in suggestions]
        assert texts[0] == ONBOARDING_QUESTIONS_BASE[0]
        assert ONBOARDING_UPLOAD_QUESTION in texts

    def test_get_suggestions_respects_limit(self) -> None:
        sample_chunks = [
            _chunk(f"doc{i}.pdf", "body", section_title="Some Heading Text", document_title=f"Doc {i}")
            for i in range(5)
        ]

        class _Store:
            chunks_value = sample_chunks

            @property
            def chunks(self):
                return self.chunks_value

        service = SuggestedQuestionService(_Store())
        authorized = frozenset(f"doc{i}.pdf" for i in range(5))

        suggestions = service.get_suggestions(authorized, limit=2)

        assert len(suggestions) == 2
