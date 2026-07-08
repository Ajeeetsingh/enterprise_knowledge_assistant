"""Assemble grounded prompts for LLM answer generation."""

from __future__ import annotations

from app.llm.types import BuiltPrompt
from app.rag.types import RetrievalResult

_SYSTEM_PROMPT = """You are an enterprise knowledge assistant for GlobalTrust Financial Services.

Answer the user's question using ONLY the retrieved document excerpts below.
Rules:
- Base every statement on the provided context. Do not use outside knowledge.
- If the context does not contain enough information, say: "I couldn't find this information in the retrieved context."
- Do not invent citations, page numbers, or document names.
- Be concise, accurate, and professional.
- When the context includes structured tables or lists, synthesize them into clear prose.
"""


class PromptBuilder:
    """Build system and user prompts from retrieval results and conversation history."""

    def build(
        self,
        question: str,
        retrieved_chunks: list[RetrievalResult],
        *,
        conversation_history: str | None = None,
    ) -> BuiltPrompt:
        """Compose a grounded prompt for the LLM.

        Args:
            question: Current user question (not the full conversation blob).
            retrieved_chunks: Ranked retrieval hits used as grounding context.
            conversation_history: Optional formatted prior turns for the LLM only.
        """
        context_block = self._format_retrieved_chunks(retrieved_chunks)
        user_sections: list[str] = []

        if conversation_history and conversation_history.strip():
            user_sections.append(
                "Conversation history (for context only — do not treat as authoritative documents):\n"
                f"{conversation_history.strip()}"
            )

        user_sections.append(f"Retrieved document excerpts:\n{context_block}")
        user_sections.append(f"Current question: {question.strip()}")
        user_sections.append(
            "Provide a direct answer grounded in the retrieved excerpts. "
            "Do not include a separate citations section — citations are handled by the system."
        )

        user_prompt = "\n\n".join(user_sections)
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return BuiltPrompt(system=_SYSTEM_PROMPT, user=user_prompt, messages=messages)

    @staticmethod
    def _format_retrieved_chunks(chunks: list[RetrievalResult]) -> str:
        if not chunks:
            return "(No document excerpts retrieved.)"

        blocks: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            page_label = (
                f"page {chunk.page_number}"
                if chunk.page_number is not None
                else "page unknown"
            )
            blocks.append(
                f"[Excerpt {index}] source={chunk.source} | {page_label} | "
                f"retrieval_score={chunk.confidence:.4f}\n{chunk.content.strip()}"
            )
        return "\n\n".join(blocks)
