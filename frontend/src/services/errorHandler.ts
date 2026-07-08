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
    case 500:
      return 'Server error. Please try again later.'
    default:
      return error.message || 'An unexpected error occurred.'
  }
}

/** Normalise unknown errors and return a user-facing message. */
export function getApiErrorMessage(error: unknown): string {
  return mapApiErrorToMessage(toApiError(error))
}

/** Return true when the error represents a network connectivity failure. */
export function isNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return error.code === 'ERR_NETWORK' || error.response == null
  }
  const apiError = toApiError(error)
  return apiError.status === 0
}
