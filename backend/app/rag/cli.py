"""CLI demo and interactive mode for the Enterprise RAG prototype."""

from __future__ import annotations

import json

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


def main() -> None:
    """Entry point for CLI demo."""
    run_demo()
    print("\n--- Interactive mode (optional) ---")
    interactive_mode()


if __name__ == "__main__":
    main()
