import axios from 'axios'

import type { ApiError } from '@/types'

/**
 * Normalise unknown errors into a typed {@link ApiError}.
 *
 * Handles Axios HTTP errors, network failures, and generic exceptions without
 * throwing — safe to use in UI error boundaries and auth flows.
 */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0
    const detail = error.response?.data

    let message = 'Request failed'
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object' && 'detail' in detail) {
      const nested = (detail as { detail: unknown }).detail
      message = typeof nested === 'string' ? nested : JSON.stringify(nested)
    } else if (error.message) {
      message = error.message
    }

    if (status === 0 && error.code === 'ERR_NETWORK') {
      message = 'Network error — please check your connection.'
    }

    return { message, status }
  }

  if (error instanceof Error) {
    return { message: error.message, status: 0 }
  }

  return { message: 'An unexpected error occurred.', status: 0 }
}
