"""Assemble grounded prompts for LLM answer generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm.types import BuiltPrompt
from app.rag.types import RetrievalResult

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.answer_synthesis.types import SynthesisPlan
    from app.evidence_composition.types import AnswerComposition
    from app.evidence_organization.types import EvidenceGraph


def _resolve_org_label() -> str:
    """Return tenant display name from settings, with a safe product fallback."""
    try:
        from app.config import get_settings

        settings = get_settings()
        display = (getattr(settings, "org_display_name", None) or "").strip()
        if display:
            return display
        aliases = getattr(settings, "org_aliases", None) or []
        for alias in aliases:
            cleaned = str(alias).strip()
            if cleaned:
                return cleaned
    except Exception:  # noqa: BLE001
        pass
    return "the organization"


def build_system_prompt(org_label: str | None = None) -> str:
    """Build the DOCUMENT-path system prompt for the active tenant."""
    organization = (org_label or _resolve_org_label()).strip() or "the organization"
    return f"""You are Knowra, an internal enterprise knowledge Q&A assistant for {organization}.

The uploaded / retrieved documents below are the ONLY source of truth for organization-specific answers.

Rules:
- Answer using ONLY the retrieved document excerpts provided in this prompt.
- Never use outside/world knowledge to answer enterprise questions.
- Never invent policies, procedures, values, org structures, numbers, or document names.
- Never "fill in gaps" with general knowledge when the excerpts are incomplete.
- Never suggest visiting an official website, contacting support, or other external sources for facts that should come from the uploaded documents.
- If the retrieved excerpts do not contain enough information to answer the question, say exactly: "I couldn't find this information in the retrieved context."
- Do not invent citations, page numbers, or document names.
- Be concise, accurate, and professional.
- When the context includes structured tables or lists, synthesize them into clear prose grounded only in that context.
- When an answer structure is provided, follow it for organization only; never invent facts to fill sections.
- When synthesis guidance is provided, write one coherent explanation organized by concepts — not by document boundaries.
- Never mention internal system terms such as PRIMARY, SUPPORTING, OPTIONAL, chunk ids, excerpt numbers, rerank, similarity, top-k, or section ids.
- Prefer the designated primary source for the topic; use supporting sources only to enrich.
"""


class PromptBuilder:
    """Build system and user prompts from retrieval results and conversation history."""

    def __init__(self, org_label: str | None = None) -> None:
        self._org_label = org_label

    def build(
        self,
        question: str,
        retrieved_chunks: list[RetrievalResult],
        *,
        conversation_history: str | None = None,
        answer_plan: AnswerPlan | None = None,
        evidence_graph: EvidenceGraph | None = None,
        answer_composition: AnswerComposition | None = None,
        answer_synthesis: SynthesisPlan | None = None,
    ) -> BuiltPrompt:
        """Compose a grounded prompt for the LLM.

        Args:
            question: Current user question (not the full conversation blob).
            retrieved_chunks: Ranked retrieval hits used as grounding context.
            conversation_history: Optional formatted prior turns for the LLM only.
            answer_plan: Optional Phase 4A structure plan (layout only, no facts).
            evidence_graph: Optional Phase 4B organized evidence (same chunks, regrouped).
            answer_composition: Optional Phase 4C prioritized evidence composition.
            answer_synthesis: Optional Phase 4F concept-oriented synthesis plan.
        """
        system_prompt = build_system_prompt(self._org_label)
        user_sections: list[str] = []

        if conversation_history and conversation_history.strip():
            user_sections.append(
                "Conversation history (for context only — do not treat as authoritative documents):\n"
                f"{conversation_history.strip()}"
            )

        if answer_synthesis is not None:
            user_sections.append(answer_synthesis.format_for_prompt())
        elif answer_composition is not None:
            user_sections.append(answer_composition.format_for_prompt())
        elif evidence_graph is not None:
            user_sections.append(evidence_graph.format_for_prompt())
        else:
            context_block = self._format_retrieved_chunks(retrieved_chunks)
            user_sections.append(f"Retrieved document excerpts:\n{context_block}")

        user_sections.append(f"Current question: {question.strip()}")
        if answer_plan is not None and (
            answer_synthesis is None or not answer_synthesis.is_unsupported
        ):
            user_sections.append(answer_plan.format_for_prompt())
        user_sections.append(
            "Provide a direct answer grounded ONLY in the retrieved evidence. "
            "If the evidence is insufficient, say you could not find the information "
            "in the retrieved context. "
            "Write a coherent synthesized answer — not a list of document summaries. "
            "Do not include a separate citations section — citations are handled by the system."
        )

        user_prompt = "\n\n".join(user_sections)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return BuiltPrompt(system=system_prompt, user=user_prompt, messages=messages)

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
                f"[Source {index}] source={chunk.source} | {page_label}\n"
                f"{chunk.content.strip()}"
            )
        return "\n\n".join(blocks)
