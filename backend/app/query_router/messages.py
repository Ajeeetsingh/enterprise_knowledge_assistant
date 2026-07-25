"""Shared curated messages for document-route edge cases."""

from __future__ import annotations

ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE = (
    "I can answer that using your organization's knowledge base, but you currently "
    "don't have any accessible documents to search. Once the relevant documents are "
    "available to you, I can answer with source citations."
)

INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE = (
    "I couldn't find enough relevant information in the documents available to you "
    "to answer that confidently. Try rephrasing your question, or check whether the "
    "relevant document has been uploaded and shared with your role."
)

GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE = (
    "I can answer questions from your organisation's documents once you're signed in "
    "and have access to them. Sign in to continue with document-based questions."
)

ANSWER_KIND_PRODUCT_HELP = "product_help"
ANSWER_KIND_DOCUMENT_GROUNDED = "document_grounded"
ANSWER_KIND_GENERAL = "general"
ANSWER_KIND_DOCUMENT_UNAVAILABLE = "document_unavailable"
ANSWER_KIND_DOCUMENT_INSUFFICIENT = "document_insufficient"
ANSWER_KIND_UNSAFE = "unsafe"
ANSWER_KIND_GUEST_AUTH_REQUIRED = "guest_auth_required"
