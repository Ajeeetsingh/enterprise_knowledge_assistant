# Enterprise Knowledge Assistant

# AI Development Handbook

**Version:** 1.0
**Status:** Approved

---

# 1. Purpose

This handbook defines how AI tools (Cursor, Claude, ChatGPT, etc.) should be used during the development of the Enterprise Knowledge Assistant.

The objective is **not** to let AI build the project.

The objective is to use AI as a senior development assistant while humans remain responsible for:

* Product decisions
* Architecture
* Security
* Business logic
* Code review

This handbook ensures AI-generated code remains consistent with the project's architecture and engineering standards.

---

# 2. AI-Assisted Development Philosophy

AI should:

* Accelerate development
* Reduce repetitive work
* Generate boilerplate
* Improve documentation
* Suggest improvements

AI should NOT:

* Decide architecture
* Decide product scope
* Invent project structure
* Replace engineering judgment
* Bypass code reviews

Every AI-generated change must be reviewed before acceptance.

---

# 3. Approved AI Tools

Primary

* Cursor IDE

Secondary

* ChatGPT

Optional

* Claude (large architecture discussions)

The project should remain tool-independent.

---

# 4. Model Selection Strategy

## Cursor Default / Auto

Use for:

* CRUD APIs
* SQLAlchemy models
* FastAPI routes
* Pydantic schemas
* React components
* Unit tests
* Integration tests
* Documentation formatting
* Refactoring
* Import fixes
* Bug fixes

Expected Usage

~90%

---

## Claude Sonnet (or equivalent)

Use only for:

* Architecture
* Database design
* Large refactoring
* Security reviews
* System design
* Complex debugging
* Performance discussions

Expected Usage

~10%

Never waste Sonnet requests on boilerplate.

---

# 5. Prompt Engineering Rules

Every implementation prompt should contain:

1. Context
2. Objective
3. Constraints
4. Deliverables
5. Acceptance Criteria

Example

Context

Implement Authentication.

Objective

Create secure JWT login.

Constraints

Follow folder_structure.md.

Do not modify RAG.

Deliverables

API

Services

Tests

Acceptance

All authentication tests pass.

---

# 6. Architecture Rule

Every prompt should begin with:

> Read and follow folder_structure.md as the source of truth.

This prevents AI from inventing new architectures.

---

# 7. Phase Rule

Only work on one phase at a time.

Never combine multiple phases.

Wrong

Authentication

*

Chat

*

Frontend

Correct

Authentication

↓

Review

↓

Testing

↓

Commit

↓

Next Phase

---

# 8. Definition of a Good Prompt

Every implementation prompt should include:

* Goal
* Existing context
* Files to modify
* Files not to modify
* Constraints
* Testing requirements

Avoid vague prompts such as:

"Build authentication."

Prefer:

"Implement JWT authentication using SQLAlchemy and PostgreSQL following folder_structure.md without modifying the RAG module."

---

# 9. Code Review Checklist

Every AI-generated pull request should be reviewed for:

* Architecture compliance
* Code quality
* Security
* Error handling
* Logging
* Testing
* Documentation

Never merge without review.

---

# 10. Development Workflow

Each feature follows:

1. Read relevant phase document.
2. Prepare implementation prompt.
3. Generate code.
4. Review code.
5. Refactor if necessary.
6. Run tests.
7. Manual verification.
8. Update documentation.
9. Commit changes.

Never skip testing.

---

# 11. Git Workflow

Feature branches

```text
feature/<feature-name>
```

Examples

```text
feature/authentication

feature/document-upload

feature/chat-api
```

Commit frequently.

Keep commits focused.

---

# 12. Documentation Workflow

Every feature requires:

* Code
* Tests
* Documentation

Whenever code changes:

Update

README

Relevant phase document

Architecture (if needed)

Roadmap (if needed)

---

# 13. Testing Workflow

Every implementation should include:

Unit Tests

↓

Integration Tests

↓

Enterprise Dataset Tests

↓

Manual Testing

↓

Regression Tests

Do not rely solely on manual testing.

---

# 14. Enterprise Test Data

Use realistic enterprise data.

Departments

* HR
* Finance
* IT
* Security
* Engineering
* Legal
* Operations
* Sales

Never use unrealistic placeholder examples unless testing edge cases.

---

# 15. Bug Handling

Every bug should:

1. Be reproduced.
2. Receive a failing test.
3. Be fixed.
4. Pass regression tests.

Never fix bugs without adding tests.

---

# 16. Refactoring Guidelines

Refactor only when:

* Code duplication exists.
* Maintainability improves.
* Readability improves.
* Performance benefits are measurable.

Avoid unnecessary rewrites.

---

# 17. Security Guidelines

AI-generated security code must be manually reviewed.

Examples

Authentication

Authorization

JWT

RBAC

Password hashing

File uploads

Never trust AI blindly for security-critical code.

---

# 18. Performance Guidelines

Do not optimize prematurely.

Priority order

1. Correctness
2. Readability
3. Maintainability
4. Performance

Optimize only after profiling.

---

# 19. When to Ask ChatGPT

Use ChatGPT for:

* Product discussions
* Architecture
* Phase planning
* Security design
* Technology selection
* Roadmaps
* Code reviews
* Documentation

Avoid using it for repetitive CRUD generation.

---

# 20. When to Use Cursor

Use Cursor for:

* Boilerplate
* APIs
* Models
* CRUD
* Tests
* Refactoring
* Documentation formatting
* Import management

Cursor should handle repetitive engineering work.

---

# 21. Common Mistakes to Avoid

Do not:

* Skip phases
* Skip testing
* Modify unrelated modules
* Introduce new architecture without review
* Generate huge features in one prompt
* Ignore documentation

Small, reviewable changes are preferred.

---

# 22. Definition of Done

A task is complete only when:

✓ Code implemented

✓ Tests passing

✓ Manual testing complete

✓ Documentation updated

✓ Code reviewed

✓ No critical defects remain

Only then proceed to the next task.

---

# 23. Engineering Principles

The project values:

* Simplicity
* Maintainability
* Reliability
* Security
* Scalability
* Documentation
* Testability

Every decision should support these principles.

---

# 24. Long-Term Vision

The Enterprise Knowledge Assistant should become an enterprise-grade software product, not just a portfolio project.

AI should accelerate development but never replace thoughtful engineering.

Every AI-generated contribution should move the project closer to a maintainable, secure, and production-ready system.

---

# 25. Final Rule

**AI is a development accelerator, not the architect.**

Architecture, product direction, engineering standards, and final technical decisions always remain human responsibilities.

Following this handbook ensures that AI remains a powerful collaborator while the project maintains professional engineering quality throughout its lifecycle.
