import type { BatchUploadItem } from '../hooks/useUploadDocuments'
import type { Document } from '../types'

/** Duration of the temporary list-row highlight after locating a duplicate. */
export const DUPLICATE_HIGHLIGHT_MS = 2000

/**
 * Pick the first duplicate upload that maps to a document currently rendered
 * in *visibleDocuments*. Used so batch duplicates do not scroll chaotically.
 */
export function resolveHighlightDocumentId(
  uploadItems: readonly BatchUploadItem[],
  visibleDocuments: readonly Document[],
): string | null {
  const visibleIds = new Set(visibleDocuments.map((document) => document.document_id))

  for (const item of uploadItems) {
    if (item.status !== 'duplicate') continue
    const existingId = item.existingDocumentId
    if (!existingId) continue
    if (visibleIds.has(existingId)) {
      return existingId
    }
  }

  return null
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
