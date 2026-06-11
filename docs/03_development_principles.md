# Enterprise Knowledge Assistant

# Development Principles

**Version:** 1.0
**Status:** Approved

---

# 1. Purpose

This document defines the engineering principles, coding standards, architectural rules, and development workflow for the Enterprise Knowledge Assistant.

Every contributor should follow these guidelines to ensure the project remains maintainable, scalable, secure, and production-ready.

These principles are mandatory unless explicitly revised.

---

# 2. Core Engineering Philosophy

The project follows five core principles:

1. Build for maintainability over speed.
2. Solve business problems, not technical curiosities.
3. Keep the architecture simple until complexity is justified.
4. Every feature must be testable.
5. Documentation is part of the implementation.

---

# 3. Product-First Development

Every feature must answer these questions before implementation:

* What business problem does it solve?
* Who benefits from it?
* Why is it required in the MVP?
* Can it wait until Version 2?

If a feature has no measurable business value, it should not be implemented.

---

# 4. Architecture Rules

The approved architecture is the source of truth.

No feature may violate the layered architecture.

```text
Frontend
        ↓
API
        ↓
Services
        ↓
Domain (RAG)
        ↓
Infrastructure
```

Never reverse dependencies.

---

# 5. Single Responsibility Principle

Every module should have one responsibility.

Examples:

Good

Authentication

* Login
* JWT
* Password hashing

Bad

Authentication module also uploads documents.

---

# 6. Folder Ownership

Every folder owns a specific responsibility.

## api/

HTTP only.

Contains:

* Routes
* Request validation
* Response formatting

No business logic.

---

## services/

Business workflows.

Coordinates modules.

No HTTP handling.

---

## rag/

Owns:

* Retrieval
* Routing
* Citations
* Answer generation
* Confidence scoring

No database logic.

---

## ingestion/

Owns:

* File parsing
* Chunking
* Embeddings
* Indexing

---

## auth/

Owns:

* Authentication
* JWT
* Password hashing

---

## rbac/

Owns:

Authorization only.

---

## db/

Owns:

* Models
* Sessions
* Database configuration

---

## audit/

Owns:

* Audit logging
* Compliance records

---

# 7. API Principles

Every API should:

* Follow REST conventions.
* Return consistent responses.
* Use appropriate HTTP status codes.
* Validate all inputs.

Never expose internal implementation details.

---

# 8. Service Layer Rules

Services contain business logic.

Services may call:

* Database
* RAG
* Audit
* Storage

Services should never depend on API routes.

---

# 9. Database Principles

Use:

* SQLAlchemy 2.x
* Alembic

All schema changes require migrations.

Never modify production tables manually.

---

# 10. RAG Principles

The RAG engine must remain independent.

The RAG module should not know:

* FastAPI
* React
* JWT
* PostgreSQL

It should only process knowledge retrieval.

This allows future reuse.

---

# 11. Security Principles

Security is mandatory.

Requirements:

* JWT authentication
* RBAC
* Password hashing
* Input validation
* Audit logging

Never trust client-side validation.

---

# 12. Error Handling

Never expose stack traces.

Use standardized error responses.

Every error should be logged.

---

# 13. Logging Principles

Use structured logging.

Log:

* Request
* Duration
* User
* Endpoint
* Errors

Sensitive information must never be logged.

---

# 14. Documentation Rules

Every feature requires:

* Code
* Tests
* Documentation

Documentation is not optional.

---

# 15. Testing Principles

Every phase must include:

Unit Tests

Integration Tests

Manual Tests

Enterprise Dataset Tests

Regression Tests

A feature is incomplete without tests.

---

# 16. Git Workflow

Main branch remains stable.

Feature development:

```text
feature/<feature-name>
```

Examples:

```text
feature/authentication

feature/document-upload

feature/chat-api
```

Merge only after review.

---

# 17. Commit Standards

Good examples:

```text
feat(auth): implement JWT authentication

feat(chat): add conversation history

fix(rag): improve retrieval confidence

docs: update deployment guide

test(upload): add PDF upload tests
```

Avoid vague commits.

---

# 18. Cursor Usage Guidelines

Use Cursor for:

* Boilerplate
* CRUD
* API generation
* SQLAlchemy models
* Tests
* Refactoring

Do not rely on Cursor for:

* Product decisions
* System architecture
* Security design
* Database design
* Business logic

These should be reviewed manually.

---

# 19. Model Usage Strategy

Use Sonnet for:

* Architecture
* Large refactoring
* Complex debugging
* Database design
* Security design

Use Cursor Default/Auto for:

* CRUD
* API routes
* SQLAlchemy
* Pydantic schemas
* React components
* Tests
* Documentation formatting

Goal:

Approximately 10% Sonnet and 90% Default/Auto.

---

# 20. Code Review Checklist

Before merging:

* Architecture respected
* No duplicated code
* Tests pass
* Documentation updated
* Logging added
* Security considered
* Error handling implemented

---

# 21. Definition of Done

A task is complete only when:

✓ Feature implemented

✓ Unit tests pass

✓ Integration tests pass

✓ Manual testing completed

✓ Documentation updated

✓ Code reviewed

✓ No critical issues remain

---

# 22. MVP Development Rules

Do not implement future features early.

Avoid:

* Microservices
* Kubernetes
* Multi-tenancy
* Redis
* Event-driven architecture
* AI agents

Keep the MVP focused.

---

# 23. Performance Guidelines

Optimize only when necessary.

Current priorities:

1. Correctness
2. Maintainability
3. Readability
4. Performance

Premature optimization is discouraged.

---

# 24. Technical Debt Policy

Small technical debt is acceptable during MVP.

However:

* It must be documented.
* It must not compromise architecture.
* It must have a future resolution plan.

---

# 25. Long-Term Engineering Vision

The Enterprise Knowledge Assistant should evolve into an enterprise-grade software platform.

Every implementation should be evaluated against one question:

> "Will this design still make sense when the platform has thousands of users, millions of documents, and multiple engineering teams?"

If the answer is yes, the implementation is likely aligned with the project's long-term vision.

---

# 26. Final Principle

The goal of this project is not to build a RAG demo.

The goal is to build a production-quality enterprise software product using modern software engineering practices, AI, and scalable architecture.

Every line of code should move the product closer to that goal.
