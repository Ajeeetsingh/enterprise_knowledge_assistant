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

export const VISIBILITY_NOT_IN_LIST_API =
  'Visibility is stored in the backend but not returned by GET /documents or GET /documents/{id}.'
