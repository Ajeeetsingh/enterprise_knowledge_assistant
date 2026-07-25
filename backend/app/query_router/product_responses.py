"""Context-aware resolution of curated product-help answers."""

from __future__ import annotations

from app.query_router.product_intents import (
    CAPABILITIES_NO_DOCUMENTS,
    CAPABILITIES_WITH_DOCUMENTS,
    PRODUCT_INTENTS,
    ProductIntent,
    UPLOAD_INSTRUCTIONS,
    UPLOAD_NO_PERMISSION,
    get_product_intent,
)
from app.query_router.types import UserQueryContext


def resolve_product_answer(intent: ProductIntent, context: UserQueryContext) -> str:
    """Return the curated response for *intent*, tailored to *context*."""
    if intent.id == "capabilities":
        if context.has_accessible_documents:
            return CAPABILITIES_WITH_DOCUMENTS
        return CAPABILITIES_NO_DOCUMENTS

    if intent.id in {"upload_documents", "multi_file_upload"}:
        if not context.can_upload:
            return UPLOAD_NO_PERMISSION
        if intent.id == "upload_documents":
            return UPLOAD_INSTRUCTIONS
        return intent.response

    if intent.id == "who_deletes":
        # Employees/Finance typically cannot delete; keep the factual role answer
        # but add a personal note when the user lacks delete-capable roles.
        role = context.role_name
        if role in {"Employee", "Finance", "HR"}:
            return (
                f"{intent.response}\n\n"
                f"Your current role is **{role}**, which does not include "
                "document deletion in the default permission map."
            )
        return intent.response

    if intent.id == "what_can_ask":
        if not context.has_accessible_documents:
            return (
                f"{intent.response}\n\n"
                "You don't currently have searchable documents available. "
                "Product-help questions still work; document questions will "
                "return results once authorized documents are added."
            )
        return intent.response

    return intent.response


def resolve_product_answer_by_id(intent_id: str, context: UserQueryContext) -> str | None:
    """Resolve a curated answer by intent ID, or ``None`` if unknown."""
    intent = get_product_intent(intent_id)
    if intent is None:
        return None
    return resolve_product_answer(intent, context)


def all_product_intents() -> tuple[ProductIntent, ...]:
    """Expose the curated catalogue for matchers and tests."""
    return PRODUCT_INTENTS
