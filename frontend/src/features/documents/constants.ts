/** Supported upload extensions — mirrors backend `SUPPORTED_EXTENSIONS`. */
export const SUPPORTED_DOCUMENT_EXTENSIONS = [
  '.pdf',
  '.txt',
  '.csv',
  '.json',
  '.docx',
  '.xlsx',
] as const

export const SUPPORTED_DOCUMENT_ACCEPT = SUPPORTED_DOCUMENT_EXTENSIONS.join(',')

/** Mirrors backend `MAX_FILE_SIZE_BYTES` (50 MB). */
export const MAX_DOCUMENT_FILE_SIZE_BYTES = 50 * 1024 * 1024

export const MAX_DOCUMENT_FILE_SIZE_MB = 50

/** Maximum files per upload batch (UI selection / one upload action). */
export const MAX_BATCH_UPLOAD_FILES = 10

/** Maximum simultaneous single-document upload requests. */
export const MAX_CONCURRENT_UPLOADS = 3

/**
 * HTTP timeout for document upload requests.
 * Ingestion (parse → chunk → embed → index) runs synchronously on the server and
 * can exceed the default 30s API client timeout for PDFs.
 */
export const UPLOAD_REQUEST_TIMEOUT_MS = 5 * 60 * 1000

export const VISIBILITY_NOT_IN_LIST_API =
  'Visibility is stored in the backend but not returned by GET /documents or GET /documents/{id}.'
