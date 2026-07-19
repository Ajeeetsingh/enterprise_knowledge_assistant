"""Unit tests for heading-weighted retrieval text construction."""

from __future__ import annotations

from app.ingestion.retrieval_text import build_retrieval_text, resolve_chunk_heading


class TestResolveChunkHeading:
    def test_prefers_section_title(self) -> None:
        assert (
            resolve_chunk_heading("Who are the main issuers?", ("Overview", "Issuers"))
            == "Who are the main issuers?"
        )

    def test_falls_back_to_hierarchy_path(self) -> None:
        assert resolve_chunk_heading(None, ("Overview", "Issuers")) == "Issuers"

    def test_returns_none_when_nothing_known(self) -> None:
        assert resolve_chunk_heading(None, None) is None
        assert resolve_chunk_heading("", ()) is None


class TestBuildRetrievalText:
    def test_repeats_heading_ahead_of_body(self) -> None:
        text = build_retrieval_text(
            "Body content about commercial paper.",
            "Who are the main issuers?",
            repetitions=2,
        )
        assert text.count("Who are the main issuers?") == 2
        assert text.endswith("Body content about commercial paper.")

    def test_no_heading_returns_content_unchanged(self) -> None:
        content = "Body content with no known heading."
        assert build_retrieval_text(content, None) == content
        assert build_retrieval_text(content, "  ") == content

    def test_zero_repetitions_returns_content_unchanged(self) -> None:
        content = "Body content."
        assert build_retrieval_text(content, "Heading", repetitions=0) == content

    def test_does_not_mutate_original_content_string(self) -> None:
        content = "Body content."
        result = build_retrieval_text(content, "Heading")
        assert content == "Body content."
        assert result != content
