import axios from 'axios'

import type { ApiError } from '@/types'

/** True when *value* is already a normalised {@link ApiError}. */
export function isApiError(value: unknown): value is ApiError {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Partial<ApiError>
  return typeof candidate.message === 'string' && typeof candidate.status === 'number'
}

function readExistingDocumentId(detail: object): string | undefined {
  if (
    'existing_document_id' in detail &&
    typeof (detail as { existing_document_id: unknown }).existing_document_id === 'string'
  ) {
    const value = (detail as { existing_document_id: string }).existing_document_id.trim()
    return value || undefined
  }
  return undefined
}

function buildApiError(
  message: string,
  status: number,
  code?: string,
  existingDocumentId?: string,
): ApiError {
  const error: ApiError = { message, status }
  if (code) error.code = code
  if (existingDocumentId) error.existingDocumentId = existingDocumentId
  return error
}

/**
 * Normalise unknown errors into a typed {@link ApiError}.
 *
 * Handles Axios HTTP errors, already-normalised {@link ApiError} objects,
 * network failures, and generic exceptions without throwing — safe to use in
 * UI error boundaries and auth flows.
 */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0
    const detail = error.response?.data

    let message = 'Request failed'
    let code: string | undefined
    let existingDocumentId: string | undefined
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      if ('detail' in detail) {
        const nested = (detail as { detail: unknown }).detail
        message = typeof nested === 'string' ? nested : JSON.stringify(nested)
      }
      if ('code' in detail && typeof (detail as { code: unknown }).code === 'string') {
        code = (detail as { code: string }).code
      }
      existingDocumentId = readExistingDocumentId(detail)
    } else if (error.message) {
      message = error.message
    }

    if (status === 0 && error.code === 'ERR_NETWORK') {
      message = 'Network error — please check your connection.'
    }

    return buildApiError(message, status, code, existingDocumentId)
  }

  if (isApiError(error)) {
    return buildApiError(
      error.message,
      error.status,
      error.code,
      error.existingDocumentId,
    )
  }

  if (error instanceof Error) {
    return { message: error.message, status: 0 }
  }

  return { message: 'An unexpected error occurred.', status: 0 }
}
