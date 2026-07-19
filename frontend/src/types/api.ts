/** Cross-cutting API error shape returned by {@link toApiError}. */
export interface ApiError {
  message: string
  status: number
  /** Optional stable API error code (e.g. DUPLICATE_DOCUMENT). */
  code?: string
  /**
   * Public document ID for an authorized duplicate match.
   * Absent when the caller is not allowed to know about the existing document.
   */
  existingDocumentId?: string
}
