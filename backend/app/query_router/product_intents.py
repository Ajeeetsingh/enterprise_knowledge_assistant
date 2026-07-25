"""Curated product-knowledge intents for PRODUCT_HELP routing.

Approximately 30 canonical intents with example phrasings and curated
responses. Do not invent product capabilities that are not implemented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductIntent:
    """One product-help intent with example phrasings and a default response."""

    id: str
    examples: tuple[str, ...]
    response: str
    category: str = "general"


# ---------------------------------------------------------------------------
# Shared response fragments (kept accurate to the implemented product)
# ---------------------------------------------------------------------------

_CAPABILITIES_BASE = (
    "I'm Knowra. I answer natural-language "
    "questions using documents your organisation has uploaded — with "
    "citations so you can open the source and see where an answer came from.\n\n"
    "I also answer questions about how this product works (roles, uploads, "
    "citations, and access)."
)

CAPABILITIES_NO_DOCUMENTS = (
    f"{_CAPABILITIES_BASE}\n\n"
    "Right now you don't have any documents available to search. Once "
    "documents you can access are uploaded and processed, ask about their "
    "policies, procedures, or content and I'll ground answers in those sources."
)

CAPABILITIES_WITH_DOCUMENTS = (
    f"{_CAPABILITIES_BASE}\n\n"
    "You currently have documents available to search. Ask about their "
    "content and I'll retrieve relevant passages, answer from that evidence, "
    "and cite the sources (including page numbers when available)."
)

UPLOAD_INSTRUCTIONS = (
    "Users with upload permission (Admin or HR) can add documents from the "
    "**Documents** page (or Admin → Uploads):\n\n"
    "1. Choose **Upload** and select one or more files (up to 10 per batch).\n"
    "2. Supported formats: PDF, TXT, CSV, JSON, DOCX, and XLSX (max 50 MB each).\n"
    "3. Wait until status becomes searchable — then the content can be used in chat.\n\n"
    "Duplicate content (same checksum) is detected so identical files aren't "
    "ingested twice."
)

UPLOAD_NO_PERMISSION = (
    "Your account doesn't have permission to upload documents. "
    "Uploads are available to Admin and HR roles. Ask an administrator if you "
    "need a document added, or ask questions about documents that are already "
    "available to you."
)

WHAT_CAN_ASK = (
    "You can ask:\n\n"
    "• Questions about organisational documents you are allowed to read "
    "(policies, handbooks, reports, and similar).\n"
    "• Questions about this assistant itself — how uploads, citations, "
    "roles, and access work.\n\n"
    "Answers about documents are grounded in retrieved passages and include "
    "citations. I won't invent document content that isn't in your authorized sources."
)

HOW_IT_WORKS = (
    "Here's how the product works at a high level:\n\n"
    "1. Authorized users upload documents.\n"
    "2. Each file is validated, stored, parsed, chunked, embedded, and indexed.\n"
    "3. When you ask a document question, retrieval searches only sources you "
    "are allowed to see (fail-closed authorization).\n"
    "4. Relevant passages are ranked and an answer is generated with citations.\n\n"
    "You can open a citation to view the source document, jump to the cited "
    "page, and (when possible) see the matching passage highlighted."
)

SUPPORTED_FORMATS = (
    "Supported upload formats are: **PDF**, **TXT**, **CSV**, **JSON**, "
    "**DOCX**, and **XLSX**. Each file may be up to **50 MB**. "
    "You can upload up to **10 files** in one batch."
)

MULTI_UPLOAD = (
    "Yes — multi-file upload is supported. Select up to **10 files** per batch "
    "(50 MB each). Files are processed individually; status is shown per document."
)

DUPLICATES = (
    "Duplicate detection uses a content checksum (SHA-256). If you upload a "
    "file whose content already exists, the system treats it as an exact "
    "duplicate instead of creating a second searchable copy. You'll see an "
    "already-exists style outcome rather than a failed ingestion."
)

PROCESSING = (
    "After upload, documents move through validation, storage, extraction, "
    "chunking, embedding, and indexing. When processing finishes successfully, "
    "status becomes **searchable** and the content can appear in chat answers. "
    "Failed stages surface as failed statuses so you can retry or investigate."
)

CITATIONS = (
    "Document answers include **citations**: source filename, a short excerpt, "
    "a confidence score, and a page number when available. Use **Open source** "
    "to open the document in a new tab, go to the cited page, and (when the "
    "PDF text layer allows) highlight the matching passage."
)

OPEN_SOURCE = (
    "**Open source** opens the cited document in a new browser tab so your "
    "chat stays open. The viewer navigates to the cited page when page "
    "metadata is available. Opening a source still requires that you are "
    "authorized to view that document."
)

HIGHLIGHTING = (
    "When you open a citation, the viewer tries to highlight the cited "
    "passage on that page by matching the excerpt against the PDF text layer. "
    "If the text can't be located (for example a scanned page without text), "
    "the page still opens — highlighting is progressive enhancement, not a "
    "hard requirement."
)

CONVERSATIONS = (
    "Chat is organised into **conversations**. You can create, rename, and "
    "delete conversations, and scroll prior messages. After the first message, "
    "a title is generated automatically when possible. Suggested questions "
    "appear on an empty conversation to help you get started."
)

EXPORT = (
    "You can export a conversation from the chat UI (for example as Markdown, "
    "PDF, plain text, or JSON, depending on the export options shown). Exports "
    "reflect the messages in that conversation, including citations when included."
)

ROLES_OVERVIEW = (
    "There are four system roles:\n\n"
    "• **Employee** — default for public registration; ask questions and read "
    "documents within ACL.\n"
    "• **Finance** — read and query finance-accessible content (no upload by default).\n"
    "• **HR** — can upload/update documents (where permitted) and query knowledge.\n"
    "• **Admin** — full administration: users, documents, analytics, monitoring.\n\n"
    "Privileged roles are assigned by an Admin — not chosen at registration."
)

DOCUMENT_ACCESS = (
    "Document access uses visibility and roles:\n\n"
    "• **public** — any authenticated user may read.\n"
    "• **restricted** — only users with an allowed role listed on the document.\n"
    "• **private** — owner and Admin only.\n\n"
    "Chat retrieval is fail-closed: only authorized filenames can become "
    "evidence. Seeing the Documents page does not mean you can upload — "
    "upload requires `document:create` (Admin/HR)."
)

ADMIN_CAPABILITIES = (
    "Admins can manage users and roles, upload and delete documents, view "
    "analytics and monitoring, export reports, and access the full knowledge "
    "assistant. Admin is also the role that assigns HR/Finance privileges."
)

HR_CAPABILITIES = (
    "HR users can upload and update documents (where permitted), read "
    "authorized documents, and ask knowledge questions. They do not get full "
    "user-administration permissions by default."
)

FINANCE_CAPABILITIES = (
    "Finance users can read authorized documents and ask knowledge questions. "
    "They do not have document upload permission by default — ask Admin or HR "
    "if a finance document needs to be added."
)

EMPLOYEE_CAPABILITIES = (
    "Employee is the default self-registered role. Employees can ask questions "
    "and open documents they are allowed to read. They cannot upload documents "
    "or manage users. An Admin can promote an account if broader access is needed."
)

PRIVACY = (
    "Answers about organisational documents are limited to sources you are "
    "authorized to read. Retrieval does not use unauthorized index entries as "
    "evidence. This application does not claim compliance certifications; "
    "access control is implemented as RBAC + document ACL + fail-closed retrieval."
)

RBAC = (
    "Access has two layers:\n\n"
    "1. **Permissions** — what actions your role may perform (upload, delete, "
    "manage users, etc.).\n"
    "2. **Document ACL** — which specific files you may read, which also "
    "constrains RAG evidence.\n\n"
    "The backend enforces both. Hiding a button in the UI is convenience only."
)

VS_CHATBOT = (
    "Unlike a general chatbot that answers from its training data alone, this "
    "assistant is built to ground organisational answers in **your uploaded "
    "documents**, apply **role and document authorization**, and return "
    "**citations** you can open. Product-help questions are answered from a "
    "curated catalogue of how this app works — not from inventing features."
)

VS_CHAT_PDF = (
    "A basic “chat with PDF” tool usually focuses on one or a few files with "
    "little access control. This product is a multi-document knowledge base "
    "with hybrid search, conversations, admin tooling, and fail-closed "
    "authorization so users only receive evidence from documents they may see."
)

HOW_SOURCED = (
    "Document answers are sourced from retrieved passages in files you can "
    "access. The assistant cites those sources so you can verify the text. "
    "If nothing relevant is found in your authorized set, you'll be told — "
    "rather than guessing from outside your documents."
)

CONFIDENCE = (
    "Each citation includes a confidence score reflecting retrieval strength "
    "for that evidence. Overall answer confidence summarises how strongly "
    "the retrieved context supports the response. Confidence is a ranking "
    "signal — always open the source when decisions depend on the exact wording."
)

WHO_DELETES = (
    "Document deletion requires the `document:delete` permission, which is "
    "granted to **Admin** in the default role map. Other roles cannot delete "
    "documents unless an Admin has assigned a role that includes that permission."
)

REGISTRATION = (
    "Anyone can register publicly. New accounts are always assigned the "
    "**Employee** role — you cannot select Admin, HR, or Finance during signup. "
    "An Admin promotes users later from user management."
)

SUGGESTIONS_HELP = (
    "Suggested questions on an empty chat are either onboarding prompts "
    "(when you don't have documents to search yet) or prompts mined from "
    "documents you are allowed to see. Clicking one sends that question into "
    "the conversation like a normal message."
)

DASHBOARD_HELP = (
    "The dashboard summarises your workspace — recent conversations, recent "
    "documents, and quick actions. Admins also see higher-level system "
    "overview links into analytics."
)


PRODUCT_INTENTS: tuple[ProductIntent, ...] = (
    ProductIntent(
        id="capabilities",
        category="capabilities",
        examples=(
            "What can this assistant help me with?",
            "What can you help me with?",
            "What do you do?",
            "What can you do?",
            "What is this assistant for?",
            "How can you help me?",
            "how can u help me",
            "Tell me what you can do",
            "What can this assistant do?",
            "What can this bot do?",
            "What are you capable of?",
        ),
        response=CAPABILITIES_NO_DOCUMENTS,
    ),
    ProductIntent(
        id="summarize_pdfs",
        category="capabilities",
        examples=(
            "Can it summarize PDFs?",
            "Can you summarize PDFs?",
            "Does the assistant summarize documents?",
            "Can this assistant summarize a PDF?",
            "Can it summarize uploaded documents?",
        ),
        response=(
            "Yes — once a PDF (or other supported file) is uploaded, processed, "
            "and searchable, you can ask the assistant to summarize that document "
            "or specific sections. Summaries of organizational documents are "
            "document-grounded answers with citations when evidence is retrieved.\n\n"
            "Supported formats include PDF, TXT, CSV, JSON, DOCX, and XLSX."
        ),
    ),
    ProductIntent(
        id="what_can_ask",
        category="capabilities",
        examples=(
            "What kinds of questions can I ask?",
            "What kinds of questions can I ask once documents are added?",
            "What can I ask you?",
            "What questions are supported?",
        ),
        response=WHAT_CAN_ASK,
    ),
    ProductIntent(
        id="how_it_works",
        category="product",
        examples=(
            "How does this product work?",
            "How does the assistant work?",
            "Explain how this knowledge assistant works",
            "Explain how Knowra works",
            "How does Knowra work?",
            "How does document Q&A work here?",
        ),
        response=HOW_IT_WORKS,
    ),
    ProductIntent(
        id="supported_formats",
        category="documents",
        examples=(
            "What document formats are supported?",
            "Which file types can I upload?",
            "What file formats are supported?",
            "Can I upload Word documents?",
        ),
        response=SUPPORTED_FORMATS,
    ),
    ProductIntent(
        id="upload_documents",
        category="documents",
        examples=(
            "How do I upload a document?",
            "How do I upload a document for the assistant to use?",
            "How can I add documents?",
            "Where do I upload files?",
            "How do I upload documents?",
        ),
        response=UPLOAD_INSTRUCTIONS,
    ),
    ProductIntent(
        id="multi_file_upload",
        category="documents",
        examples=(
            "Can I upload multiple files at once?",
            "Does multi-file upload work?",
            "How many files can I upload together?",
        ),
        response=MULTI_UPLOAD,
    ),
    ProductIntent(
        id="duplicate_documents",
        category="documents",
        examples=(
            "What happens if I upload a duplicate document?",
            "How does duplicate detection work?",
            "Why does it say the document already exists?",
        ),
        response=DUPLICATES,
    ),
    ProductIntent(
        id="document_processing",
        category="documents",
        examples=(
            "How are documents processed?",
            "What does searchable status mean?",
            "Why is my document still processing?",
        ),
        response=PROCESSING,
    ),
    ProductIntent(
        id="citations",
        category="citations",
        examples=(
            "How do citations work?",
            "What are citations?",
            "How are answers sourced?",
            "How do I see where an answer came from?",
        ),
        response=CITATIONS,
    ),
    ProductIntent(
        id="open_source",
        category="citations",
        examples=(
            "What does Open Source do?",
            "How do I open a source document?",
            "How does source viewing work?",
        ),
        response=OPEN_SOURCE,
    ),
    ProductIntent(
        id="source_highlighting",
        category="citations",
        examples=(
            "How does source highlighting work?",
            "Why is text highlighted in the PDF?",
            "Does the viewer highlight the cited passage?",
        ),
        response=HIGHLIGHTING,
    ),
    ProductIntent(
        id="conversation_history",
        category="chat",
        examples=(
            "How does conversation history work?",
            "Can I have multiple conversations?",
            "How do I rename a conversation?",
        ),
        response=CONVERSATIONS,
    ),
    ProductIntent(
        id="conversation_export",
        category="chat",
        examples=(
            "Can I export a conversation?",
            "How do I export chat history?",
            "What export formats are available?",
        ),
        response=EXPORT,
    ),
    ProductIntent(
        id="roles_overview",
        category="roles",
        examples=(
            "What user roles exist?",
            "What are the different roles?",
            "Explain the role model",
        ),
        response=ROLES_OVERVIEW,
    ),
    ProductIntent(
        id="document_permissions",
        category="access",
        examples=(
            "How does document access work?",
            "How do document permissions work?",
            "Who can see which documents?",
            "Who can see my files?",
            "How does document visibility work?",
            "How are my documents protected?",
        ),
        response=DOCUMENT_ACCESS,
    ),
    ProductIntent(
        id="admin_capabilities",
        category="roles",
        examples=(
            "What can an Admin do?",
            "What are Admin capabilities?",
            "What can administrators do in this app?",
        ),
        response=ADMIN_CAPABILITIES,
    ),
    ProductIntent(
        id="hr_capabilities",
        category="roles",
        examples=(
            "What can HR do?",
            "What are HR capabilities?",
            "What permissions does the HR role have?",
        ),
        response=HR_CAPABILITIES,
    ),
    ProductIntent(
        id="finance_capabilities",
        category="roles",
        examples=(
            "What can Finance do?",
            "What are Finance capabilities?",
            "What permissions does the Finance role have?",
        ),
        response=FINANCE_CAPABILITIES,
    ),
    ProductIntent(
        id="employee_capabilities",
        category="roles",
        examples=(
            "What can an Employee do?",
            "What are Employee capabilities?",
            "What can I do as an Employee?",
        ),
        response=EMPLOYEE_CAPABILITIES,
    ),
    ProductIntent(
        id="privacy_access",
        category="access",
        examples=(
            "How is my data access controlled?",
            "Is my data private from other roles?",
            "Can other users see my answers?",
            "How does privacy work in this assistant?",
        ),
        response=PRIVACY,
    ),
    ProductIntent(
        id="rbac",
        category="access",
        examples=(
            "How does role-based access work?",
            "What is RBAC in this product?",
            "How are permissions enforced?",
        ),
        response=RBAC,
    ),
    ProductIntent(
        id="vs_chatbot",
        category="product",
        examples=(
            "How is this different from a normal chatbot?",
            "How are you different from ChatGPT?",
            "Why not just use a regular chatbot?",
        ),
        response=VS_CHATBOT,
    ),
    ProductIntent(
        id="vs_chat_pdf",
        category="product",
        examples=(
            "How is this different from chat with PDF?",
            "How is this different from a basic Chat with PDF tool?",
            "Is this just chat with PDF?",
        ),
        response=VS_CHAT_PDF,
    ),
    ProductIntent(
        id="confidence_scores",
        category="citations",
        examples=(
            "What does confidence mean?",
            "How should I interpret confidence scores?",
            "Why do citations show a percentage?",
        ),
        response=CONFIDENCE,
    ),
    ProductIntent(
        id="who_deletes",
        category="documents",
        examples=(
            "Who can delete documents?",
            "Can I delete a document?",
            "How do I delete an uploaded file?",
        ),
        response=WHO_DELETES,
    ),
    ProductIntent(
        id="registration",
        category="roles",
        examples=(
            "How does registration work?",
            "What role do new users get?",
            "Can I register as Admin?",
        ),
        response=REGISTRATION,
    ),
    ProductIntent(
        id="suggested_questions",
        category="chat",
        examples=(
            "What are the suggested questions?",
            "How do suggested questions work?",
            "Where do example prompts come from?",
        ),
        response=SUGGESTIONS_HELP,
    ),
    ProductIntent(
        id="dashboard",
        category="product",
        examples=(
            "What is on the dashboard?",
            "What does the dashboard show?",
            "How do I use the workspace dashboard?",
        ),
        response=DASHBOARD_HELP,
    ),
    ProductIntent(
        id="how_sourced",
        category="citations",
        examples=(
            "Where do answers come from?",
            "Are answers grounded in documents?",
            "Do you make up answers?",
        ),
        response=HOW_SOURCED,
    ),
)


def get_product_intent(intent_id: str) -> ProductIntent | None:
    """Return a product intent by stable ID, or ``None``."""
    for intent in PRODUCT_INTENTS:
        if intent.id == intent_id:
            return intent
    return None
