"""CLI demo and interactive mode for the Enterprise RAG prototype."""

from __future__ import annotations

import json
from pathlib import Path

from app.rag.engine import EnterpriseRAG
from app.rag.rbac import RBACError
from app.rag.types import QueryResponse


def _print_response(response: QueryResponse) -> None:
    print("\n" + "=" * 60)
    print(f"Query:      {response.query}")
    print(f"Role:       {response.role}")
    print(f"Route:      {response.routed_category} (confidence: {response.route_confidence})")
    print(f"Access:     {'GRANTED' if response.access_granted else 'DENIED'}")
    print("-" * 60)
    if response.access_granted and response.answer:
        print(f"Answer:     {response.answer}")
        print(f"Sources:    {', '.join(response.sources_used)}")
        print(f"Confidence: {response.confidence_score}")
        if response.citations:
            print("Citations:")
            for cite in response.citations:
                preview = cite.excerpt if len(cite.excerpt) <= 80 else cite.excerpt[:80] + "..."
                print(f"  - {cite.source} ({cite.confidence}): {preview}")
    print(f"Message:    {response.message}")
    print("=" * 60)


def run_demo() -> None:
    """Run a demonstration with sample queries across roles."""
    print("Enterprise RAG Intelligence System")
    print("Loading documents and building FAISS index...")

    rag = EnterpriseRAG()
    chunk_count = rag.initialize()
    print(f"Indexed {chunk_count} document chunks.\n")

    demo_queries = [
        ("What is the remote work policy?", "employee"),
        ("What was Q3 revenue for the Sales department?", "finance"),
        ("Were there any malware incidents this week?", "admin"),
        ("Show me employee salary records", "employee"),
        ("What is the parental leave policy?", "hr"),
        ("What were the failed login attempts?", "finance"),
    ]

    for query, role in demo_queries:
        response = rag.query(query, role)
        _print_response(response)


def interactive_mode() -> None:
    """Simple interactive CLI for manual testing."""
    rag = EnterpriseRAG()
    chunk_count = rag.initialize()
    print(f"Enterprise RAG ready ({chunk_count} chunks indexed).")
    print("Enter queries as: <role> | <question>")
    print("Roles: admin, hr, finance, employee. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input or user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break

        if "|" not in user_input:
            print("Format: <role> | <question>  e.g.  hr | What is the leave policy?")
            continue

        role_part, query_part = user_input.split("|", 1)
        role = role_part.strip()
        query = query_part.strip()

        if not query:
            print("Please provide a question.")
            continue

        try:
            response = rag.query(query, role)
            print(json.dumps(response.to_dict(), indent=2))
        except (RBACError, ValueError) as exc:
            print(f"Error: {exc}")


def debug_query(query: str, *, data_dir: str | Path | None = None, top_k: int = 5) -> None:
    """Print a full retrieval diagnostics trace for one query (DEBUG mode).

    Builds a temporary FAISS + BM25 index from the fixture corpus (or
    ``data_dir`` when provided), then prints the BM25 top-K, dense top-K,
    hybrid merge, reranker top-K, and final-context stages side by side —
    each entry annotated with document, page, heading, score, and source
    (dense/BM25/both). See ``app.rag.diagnostics.explain_query``.
    """
    from app.ingestion.loader import load_documents
    from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.diagnostics import explain_query
    from app.rag.engine import DEFAULT_DATA_DIR
    from app.rag.hybrid.bm25 import BM25Index
    from app.rag.hybrid.config import HybridRetrievalSettings

    source_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    chunks = load_documents(source_dir)
    if not chunks:
        print(f"No chunks found under {source_dir}.")
        return

    provider = SentenceTransformerEmbeddingProvider()
    embeddings = provider.embed([chunk.content for chunk in chunks])

    store = FaissVectorStore()
    store.add_chunks(chunks, embeddings, document_id="cli-debug")

    hybrid_settings = HybridRetrievalSettings.from_settings()
    bm25 = BM25Index(settings=hybrid_settings)
    bm25.rebuild_from_chunks(chunks)

    trace = explain_query(query, vector_store=store, bm25_index=bm25, top_k=top_k)
    print(trace.render())


def main() -> None:
    """Entry point for CLI demo."""
    run_demo()
    print("\n--- Interactive mode (optional) ---")
    interactive_mode()


if __name__ == "__main__":
    main()
