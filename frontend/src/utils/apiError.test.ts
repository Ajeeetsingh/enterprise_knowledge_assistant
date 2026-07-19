import axios from 'axios'
import { describe, expect, it } from 'vitest'

import { isApiError, toApiError } from './apiError'

describe('toApiError', () => {
  it('preserves an already-normalised ApiError including DUPLICATE_DOCUMENT', () => {
    const normalised = {
      message: 'report.pdf has already been uploaded.',
      status: 409,
      code: 'DUPLICATE_DOCUMENT',
    }

    expect(isApiError(normalised)).toBe(true)
    expect(toApiError(normalised)).toEqual(normalised)
  })

  it('parses Axios 409 DUPLICATE_DOCUMENT responses with existing document id', () => {
    const error = new axios.AxiosError(
      'Conflict',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 409,
        statusText: 'Conflict',
        headers: {},
        config: {} as never,
        data: {
          detail: 'report.pdf has already been uploaded.',
          code: 'DUPLICATE_DOCUMENT',
          existing_document_id: 'doc-123',
        },
      },
    )

    expect(toApiError(error)).toEqual({
      message: 'report.pdf has already been uploaded.',
      status: 409,
      code: 'DUPLICATE_DOCUMENT',
      existingDocumentId: 'doc-123',
    })
  })

  it('preserves existingDocumentId on already-normalised ApiError objects', () => {
    const normalised = {
      message: 'This document has already been uploaded.',
      status: 409,
      code: 'DUPLICATE_DOCUMENT',
      existingDocumentId: 'doc-abc',
    }

    expect(toApiError(normalised)).toEqual(normalised)
  })

  it('does not treat a plain Error as a duplicate ApiError', () => {
    const result = toApiError(new Error('boom'))
    expect(result).toEqual({ message: 'boom', status: 0 })
    expect(result.code).toBeUndefined()
  })
})
