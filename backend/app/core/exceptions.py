"""Application-wide exception types."""


class EKAError(Exception):
    """Base exception for Enterprise Knowledge Assistant."""


class ServiceError(EKAError):
    """Base for service-layer errors mapped to HTTP responses by global handlers.

    Subclasses define ``status_code`` and ``public_message`` for the client-facing
    response. The ``message`` attribute retains the internal detail for logging.
    """

    status_code: int = 500
    public_message: str = "An unexpected error occurred."

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DatabaseError(EKAError):
    """Raised when a database operation fails."""


class StorageError(EKAError):
    """Raised when a filesystem storage operation fails."""


# --- RAG service errors (Phase 3) ---


class RagServiceError(ServiceError):
    """Base RAG service integration error."""

    public_message = "Failed to process knowledge request."


class RagInitializationError(RagServiceError):
    """Raised when the RAG engine cannot be initialized."""

    status_code = 503
    public_message = "Knowledge service is temporarily unavailable."


class RagRetrievalError(RagServiceError):
    """Raised when retrieval fails during query processing."""

    status_code = 500
    public_message = "Failed to process knowledge request."


# --- Authorization errors ---


class AuthorizationError(ServiceError):
    """Raised when an authenticated user lacks required access."""

    status_code = 403

    def __init__(self, message: str = "User has no assigned role.") -> None:
        self.message = message
        self.public_message = message
        super().__init__(message)


# --- Document service errors (Phase 4) ---


class DocumentServiceError(ServiceError):
    """Base document service error."""

    public_message = "Document operation failed."


class DocumentValidationError(DocumentServiceError):
    """Raised when document input fails validation."""

    status_code = 422
    public_message = "Document validation failed."


class DocumentIngestionError(DocumentServiceError):
    """Raised when the ingestion pipeline fails."""

    status_code = 500
    public_message = "Document ingestion failed."


class ParserNotFoundError(DocumentServiceError):
    """Raised when no parser is registered for the given file type."""

    status_code = 422
    public_message = "Unsupported document format."


class EmbeddingError(DocumentServiceError):
    """Raised when embedding generation fails."""

    status_code = 500
    public_message = "Failed to generate document embeddings."


class VectorStoreError(DocumentServiceError):
    """Raised when vector index operations fail."""

    status_code = 500
    public_message = "Failed to update the knowledge index."


class DocumentStorageError(DocumentServiceError):
    """Raised when document file storage operations fail."""

    status_code = 500
    public_message = "Failed to remove document file."


class DocumentNotFoundError(DocumentServiceError):
    """Raised when a requested document does not exist."""

    status_code = 404
    public_message = "Document not found."


class DocumentIntegrityError(DocumentServiceError):
    """Raised when an upload fails an integrity policy check."""

    status_code = 409
    public_message = "Document integrity check failed."
