/**
 * Centralised API error message mapping (Phase 8.7).
 */

import axios from 'axios'

import type { ApiError } from '@/types'
import { toApiError } from '@/utils/apiError'

/** Map a normalised {@link ApiError} to a user-facing message. */
export function mapApiErrorToMessage(error: ApiError): string {
  if (error.status === 0) {
    if (
      error.message.toLowerCase().includes('network') ||
      error.message.toLowerCase().includes('connection')
    ) {
      return 'Unable to connect. Please check your network and try again.'
    }
    return error.message || 'Unable to connect. Please check your network and try again.'
  }

  switch (error.status) {
    case 401:
      return 'Session expired. Please sign in again.'
    case 403:
      return 'Access denied.'
    case 404:
      return 'Resource not found.'
    case 409:
      if (error.code === 'DUPLICATE_DOCUMENT') {
        // Stable user-facing copy — do not surface internal conflict details.
        return 'This document has already been uploaded.'
      }
      return error.message || 'This document conflicts with an existing upload.'
    case 500:
      return 'Server error. Please try again later.'
    default:
      return error.message || 'An unexpected error occurred.'
  }
}

/** True when the API rejected the upload as a content duplicate. */
export function isDuplicateDocumentError(error: unknown): boolean {
  const apiError = toApiError(error)
  return apiError.status === 409 && apiError.code === 'DUPLICATE_DOCUMENT'
}

export const DUPLICATE_DOCUMENT_USER_MESSAGE =
  'This document has already been uploaded.'

/** Normalise unknown errors and return a user-facing message. */
export function getApiErrorMessage(error: unknown): string {
  return mapApiErrorToMessage(toApiError(error))
}

/**
 * Resolve a user-facing message from an unknown thrown value, falling back
 * to a caller-supplied default when no message is present.
 *
 * Deliberately more lenient than {@link getApiErrorMessage}: some call
 * sites see rejections that aren't Axios/`Error` instances (e.g. plain
 * `{ message }` objects), so this accepts anything exposing a `message`
 * property instead of requiring a normalised {@link ApiError} shape.
 */
export function resolveErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return fallback
}

/** Return true when the error represents a network connectivity failure. */
export function isNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return error.code === 'ERR_NETWORK' || error.response == null
  }
  const apiError = toApiError(error)
  return apiError.status === 0
}
