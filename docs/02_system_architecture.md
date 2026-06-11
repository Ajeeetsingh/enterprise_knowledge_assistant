# Enterprise Knowledge Assistant

# System Architecture

**Version:** 1.0
**Status:** Approved
**Architecture Style:** Monolithic Layered Architecture

---

# 1. Overview

Enterprise Knowledge Assistant follows a layered monolithic architecture.

Although the long-term vision is a SaaS platform, the MVP intentionally avoids microservices to reduce complexity while maintaining a clean separation of concerns.

The architecture emphasizes:

* Maintainability
* Security
* Scalability
* Testability
* Extensibility

Every component has a single responsibility and communicates only through well-defined interfaces.

---

# 2. High-Level Architecture

```
                    React Frontend
                           │
                           │ HTTPS
                           ▼
                  FastAPI REST API
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 Authentication      Chat Service     Document Service
        │                  │                  │
        └──────────────┬───┴──────────────────┘
                       ▼
                  RAG Service
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
 Document        Vector Search    Answer Generator
 Ingestion          (FAISS)
        │
        ▼
 Sentence Transformers
        │
        ▼
 PostgreSQL + Local Storage
```

---

# 3. Architectural Principles

The system follows these principles.

## Layered Design

```
Presentation

↓

API

↓

Services

↓

Domain (RAG)

↓

Database / Storage
```

Every layer communicates only with the layer below it.

---

## Separation of Concerns

Each module owns exactly one responsibility.

Example

Authentication never performs document retrieval.

RAG never performs HTTP handling.

API routes never contain business logic.

---

## Dependency Direction

```
API

↓

Services

↓

Domain

↓

Infrastructure
```

Never the reverse.

---

# 4. Backend Architecture

```
backend/

app/

api/

services/

rag/

ingestion/

auth/

rbac/

audit/

db/

storage/

core/

schemas/
```

---

## API Layer

Purpose

* Accept requests
* Validate inputs
* Return responses

Responsibilities

* Request validation
* Authentication dependency injection
* HTTP status codes

Never:

* Query database directly
* Run RAG
* Generate answers

---

## Service Layer

Purpose

Business orchestration.

Examples

```
Chat Service

↓

RAG Service

↓

Audit Service
```

Services coordinate the system.

---

## RAG Layer

Purpose

The AI engine.

Contains

* Retrieval
* Routing
* Answer Generation
* Citations
* Confidence

No HTTP code.

No SQL.

No frontend logic.

---

## Ingestion Layer

Purpose

Convert documents into searchable knowledge.

Pipeline

```
Upload

↓

Validate

↓

Parse

↓

Chunk

↓

Categorize

↓

Embedding

↓

Index

↓

Persist Metadata
```

---

## Authentication Layer

Responsibilities

* Login
* JWT
* Password Hashing
* User Identity

Future

* OAuth
* SSO

---

## RBAC Layer

Responsibilities

Role authorization.

Example

```
Employee

↓

HR Documents

✓

Finance Documents

✗
```

Future

Document-level permissions.

---

## Audit Layer

Purpose

Track every important action.

Examples

* Login
* Upload
* Delete
* Query
* Access Denied

---

## Database Layer

Stores

* Users
* Documents
* Metadata
* Conversations
* Messages
* Audit Logs

Embeddings remain outside PostgreSQL during MVP.

---

## Storage Layer

Stores

Uploaded documents.

Current

```
Local Filesystem
```

Future

```
Amazon S3

Azure Blob

Google Cloud Storage
```

---

# 5. Frontend Architecture

React

```
Pages

↓

Components

↓

Hooks

↓

API Client
```

The frontend never talks directly to:

* Database
* FAISS
* Filesystem

Everything goes through FastAPI.

---

# 6. RAG Architecture

```
Question

↓

RBAC

↓

Query Router

↓

Retriever

↓

Top-K Chunks

↓

Answer Generator

↓

Citation Builder

↓

Confidence Calculator

↓

Response
```

---

# 7. Document Processing Pipeline

```
PDF

DOCX

TXT

CSV

JSON

XLSX

↓

Loader

↓

Text Extraction

↓

Chunking

↓

Metadata

↓

Embedding

↓

FAISS

↓

Ready
```

---

# 8. Authentication Flow

```
User Login

↓

Verify Credentials

↓

Generate JWT

↓

Store Token

↓

Authenticated Requests
```

---

# 9. Chat Flow

```
User

↓

Question

↓

JWT Validation

↓

RBAC

↓

Retrieve Context

↓

Generate Answer

↓

Store Conversation

↓

Return Answer
```

---

# 10. Upload Flow

```
Upload File

↓

Validation

↓

Store File

↓

Extract Text

↓

Chunk

↓

Embedding

↓

Update Index

↓

Ready
```

---

# 11. Data Storage

## PostgreSQL

Stores

* Users
* Roles
* Documents
* Conversations
* Audit Logs

---

## Local Storage

Stores

* Uploaded files

---

## FAISS

Stores

Vector embeddings.

---

# 12. Security Architecture

Layers

```
JWT

↓

RBAC

↓

Document Permissions

↓

Audit Logging
```

Every request passes through security.

---

# 13. Error Handling

All APIs return standardized errors.

Example

```
401 Unauthorized

403 Forbidden

404 Not Found

422 Validation Error

500 Internal Server Error
```

---

# 14. Logging Strategy

Structured logging only.

Every request logs:

* User
* Endpoint
* Duration
* Status
* Errors

Audit logs remain separate.

---

# 15. Scalability Strategy

Current

* Monolith
* Local Storage
* FAISS

Future

* pgvector
* S3
* Multi-tenancy
* Redis
* Kubernetes

No architectural rewrite required.

---

# 16. Design Decisions

## Why Monolith?

Faster development.

Simpler deployment.

Easier debugging.

Suitable for MVP.

---

## Why FastAPI?

High performance.

Automatic OpenAPI.

Excellent typing.

Modern async support.

---

## Why PostgreSQL?

Reliable.

Open source.

Enterprise proven.

---

## Why FAISS?

Fast.

Lightweight.

Easy local deployment.

Ideal MVP vector search.

---

## Why React?

Component architecture.

Large ecosystem.

Excellent TypeScript support.

---

# 17. Future Evolution

Version 2

* Slack
* Teams
* SharePoint
* Google Drive
* SSO
* Multi-tenancy
* pgvector
* Hybrid Search
* Workflow Automation

---

# 18. Architecture Rules

Every future feature must follow these rules.

* API contains no business logic.
* Services orchestrate workflows.
* RAG remains isolated.
* Authentication remains independent.
* RBAC enforced server-side.
* Database accessed only through service layer.
* Every new feature includes tests.
* Every feature updates documentation.
* Backward compatibility maintained whenever possible.

---

# 19. Conclusion

This architecture provides a clean, modular, and production-ready foundation for the Enterprise Knowledge Assistant MVP.

It prioritizes maintainability and simplicity while providing a clear evolution path toward an enterprise-grade SaaS platform without requiring fundamental architectural changes.
