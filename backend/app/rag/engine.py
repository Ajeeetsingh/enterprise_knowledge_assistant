"""Enterprise RAG orchestrator."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.loader import load_documents
from app.rag.answer_generator import AnswerGenerator
from app.rag.rbac import check_access, get_accessible_categories, validate_role
from app.rag.retriever import RetrievalResult, SemanticRetriever
from app.rag.router import route_query
from app.rag.types import CITATION_EXCERPT_LENGTH, Citation, QueryResponse

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"


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
            )
        )

    return citations


class EnterpriseRAG:
    """Coordinates document loading, routing, RBAC, retrieval, and answer generation."""

    def __init__(self, data_dir: str | Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.retriever = SemanticRetriever()
        self.answer_generator = AnswerGenerator()
        self._initialized = False

    def initialize(self) -> int:
        """Load documents and build the FAISS index."""
        chunks = load_documents(self.data_dir)
        self.retriever.build_index(chunks)
        self._initialized = True
        return len(chunks)

    def query(self, user_query: str, role: str) -> QueryResponse:
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
        results = self.retriever.search(
            user_query,
            top_k=3,
            allowed_categories=allowed_categories,
        )

        if not results:
            return QueryResponse(
                query=user_query,
                role=normalized_role,
                routed_category=route.category,
                route_confidence=route.confidence,
                answer="No relevant documents found for this query.",
                sources_used=[],
                citations=[],
                confidence_score=0.0,
                access_granted=True,
                message="Search completed but no matching chunks were found.",
            )

        generated = self.answer_generator.generate(user_query, results)
        citations = _build_citations(results)
        sources_label = ", ".join(generated.sources_used)

        return QueryResponse(
            query=user_query,
            role=normalized_role,
            routed_category=route.category,
            route_confidence=route.confidence,
            answer=generated.answer,
            sources_used=generated.sources_used,
            citations=citations,
            confidence_score=generated.confidence_score,
            access_granted=True,
            message=f"Answer generated from {sources_label}.",
        )
