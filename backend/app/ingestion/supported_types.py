"""Supported document MIME types and extensions."""

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf",
    ".txt",
    ".csv",
    ".json",
    ".docx",
    ".xlsx",
})

EXTENSION_TO_MIME: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".txt":  "text/plain",
    ".csv":  "text/csv",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
