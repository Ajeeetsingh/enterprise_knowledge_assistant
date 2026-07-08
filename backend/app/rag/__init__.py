"""RAG engine package."""

from app.rag.types import Citation, QueryResponse

__all__ = ["Citation", "QueryResponse", "EnterpriseRAG"]


def __getattr__(name: str):
    if name == "EnterpriseRAG":
        from app.rag.engine import EnterpriseRAG

        return EnterpriseRAG
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
