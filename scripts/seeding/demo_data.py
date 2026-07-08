"""Seed sample documents and analytics activity for manual testing.

Usage:
    python scripts/seed_database.py --demo
    python scripts/seed_database.py --demo --skip-chat
    python scripts/seed_database.py --demo --analytics-only

Uploads enterprise sample documents, records login/chat audit events, and
optionally runs real RAG chat turns so analytics dashboards populate quickly.

Requires:
    - PostgreSQL running with migrations applied (``alembic upgrade head``)
    - Roles and users seeded (``seed_database.py --roles``, ``--admin``, ``--demo``)

The first run with chat enabled downloads the embedding model (~90 MB).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.retrieval_authorization import RetrievalAuthorizationService
from app.core.exceptions import RagInitializationError, RagRetrievalError
from app.db.models import User
from app.db.repositories.document_repository import DocumentRepository
from app.db.session import SessionLocal
from app.ingestion.supported_types import EXTENSION_TO_MIME
from app.services import auth_audit_integration, chat_audit_integration
from app.services.audit_service import build_audit_service
from app.services.conversation_chat_service import build_conversation_chat_service
from app.services.conversation_service import build_conversation_service
from app.services.document_service import get_document_service
from app.services.rag_service import get_rag_service

SAMPLE_DOCS_DIR = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"

DEMO_CHAT_TURNS: tuple[tuple[str, str, str], ...] = (
    ("admin@example.com", "Admin demo chat", "What is the parental leave policy?"),
    ("admin@example.com", "Admin demo chat", "What are the password requirements?"),
    ("hr@example.com", "HR demo chat", "What is the remote work policy?"),
    ("finance@example.com", "Finance demo chat", "What was Q3 revenue for the Sales department?"),
    ("employee@example.com", "Employee demo chat", "What is the expense reimbursement process?"),
    ("employee@example.com", "Employee demo chat", "What is the quantum computing roadmap?"),
)


def _load_user(session, email: str) -> User | None:
    return session.scalar(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )


def _primary_role_name(user: User) -> str:
    priority = {"Admin": 0, "HR": 1, "Finance": 2, "Employee": 3}
    primary = min(user.roles, key=lambda role: priority.get(role.name, 99))
    return primary.name


def _authorized_sources(session, user: User) -> frozenset[str] | None:
    repository = DocumentRepository(session)
    all_docs, _ = repository.list(limit=10_000, offset=0)
    candidate_sources = frozenset(doc.filename for doc in all_docs)
    return RetrievalAuthorizationService.get_authorized_sources(
        user,
        candidate_sources,
        repository,
        query_id=str(uuid.uuid4()),
    )


def upload_sample_documents(session) -> int:
    """Upload fixture documents as the admin user."""
    admin = _load_user(session, "admin@example.com")
    if admin is None:
        print("Error: admin@example.com not found. Run seed_database.py --admin first.")
        return 0

    if not SAMPLE_DOCS_DIR.is_dir():
        print(f"Error: sample docs directory not found: {SAMPLE_DOCS_DIR}")
        return 0

    document_service = get_document_service()
    repository = DocumentRepository(session)
    uploaded = 0

    for path in sorted(SAMPLE_DOCS_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in EXTENSION_TO_MIME:
            continue

        content = path.read_bytes()
        mime = EXTENSION_TO_MIME[path.suffix.lower()]
        result = document_service.upload_document(
            repository,
            filename=path.name,
            content_type=mime,
            content=content,
            uploaded_by=admin.id,
        )
        uploaded += 1
        print(f"  {path.name}: {result.status.value} — {result.message}")

    return uploaded


def seed_audit_activity(session) -> None:
    """Record login and failure audit events for analytics dashboards."""
    audit_service = build_audit_service(session)

    login_users = (
        "admin@example.com",
        "hr@example.com",
        "finance@example.com",
        "employee@example.com",
    )
    for email in login_users:
        user = _load_user(session, email)
        if user is None:
            print(f"  skip login audit for missing user {email}")
            continue
        auth_audit_integration.record_login_success(
            audit_service,
            user_id=user.id,
            email=user.email,
            username=user.username,
            ip_address="127.0.0.1",
            user_agent="seed_demo_data.py",
        )
        print(f"  login success audit: {email}")

    auth_audit_integration.record_login_failed(
        audit_service,
        email="unknown@example.com",
        reason="Invalid email or password.",
        ip_address="127.0.0.1",
        user_agent="seed_demo_data.py",
    )
    auth_audit_integration.record_login_failed(
        audit_service,
        email="employee@example.com",
        reason="Invalid email or password.",
        ip_address="127.0.0.1",
        user_agent="seed_demo_data.py",
    )
    print("  login failure audits recorded")


def seed_chat_activity(session) -> None:
    """Run conversation chat turns and persist audit events."""
    audit_service = build_audit_service(session)
    conversation_service = build_conversation_service(session)
    chat_service = build_conversation_chat_service(session)
    rag_service = get_rag_service()

    try:
        chunk_count = rag_service.initialize()
        print(f"  RAG index initialized ({chunk_count} chunks)")
    except RagInitializationError as exc:
        print(f"Warning: RAG initialization failed: {exc}")
        print("  Skipping chat seeding. Upload documents first or run without --analytics-only.")
        return

    for email, title, question in DEMO_CHAT_TURNS:
        user = _load_user(session, email)
        if user is None:
            print(f"  skip chat for missing user {email}")
            continue

        conversation = conversation_service.create_conversation(user, title=title)
        chat_audit_integration.record_question_asked(
            audit_service,
            user_id=user.id,
            conversation_id=conversation.id,
            query_length=len(question),
            ip_address="127.0.0.1",
            user_agent="seed_demo_data.py",
        )

        try:
            result = chat_service.ask_question(
                user,
                conversation.id,
                question,
                _primary_role_name(user),
                rag_service,
                _authorized_sources(session, user),
            )
            chat_audit_integration.record_answer_generated(
                audit_service,
                user_id=user.id,
                conversation_id=result.conversation_id,
                citation_count=len(result.citations),
                confidence_score=result.confidence_score,
                ip_address="127.0.0.1",
                user_agent="seed_demo_data.py",
            )
            print(f"  chat OK ({email}): {question[:48]}...")
        except RagRetrievalError as exc:
            chat_audit_integration.record_retrieval_failed(
                audit_service,
                user_id=user.id,
                conversation_id=conversation.id,
                reason=exc.public_message,
                ip_address="127.0.0.1",
                user_agent="seed_demo_data.py",
            )
            print(f"  chat retrieval failed ({email}): {question[:48]}...")


def seed_demo_data(*, skip_chat: bool = False, analytics_only: bool = False) -> int:
    """Seed documents and optional chat/analytics activity."""
    with SessionLocal() as session:
        if analytics_only:
            print("Recording analytics audit activity only...")
            seed_audit_activity(session)
            session.commit()
            return 0

        print("Uploading sample documents...")
        uploaded = upload_sample_documents(session)
        session.commit()
        print(f"Processed {uploaded} sample document(s).")

        print("Recording login audit activity...")
        seed_audit_activity(session)
        session.commit()

        if skip_chat:
            print("Skipping chat seeding (--skip-chat).")
            return 0

        print("Running demo chat turns (first run may download the embedding model)...")
        seed_chat_activity(session)
        session.commit()

    print("Demo data seeding complete.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Upload documents and audit events only; skip RAG chat turns.",
    )
    parser.add_argument(
        "--analytics-only",
        action="store_true",
        help="Record login/failure audit events only (no uploads or chat).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_chat and args.analytics_only:
        print("Error: --skip-chat and --analytics-only cannot be used together.")
        return 1
    return seed_demo_data(skip_chat=args.skip_chat, analytics_only=args.analytics_only)


if __name__ == "__main__":
    sys.exit(main())
