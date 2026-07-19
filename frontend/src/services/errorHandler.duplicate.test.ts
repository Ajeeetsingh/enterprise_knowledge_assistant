import axios from 'axios'
import { describe, expect, it } from 'vitest'

import {
  DUPLICATE_DOCUMENT_USER_MESSAGE,
  getApiErrorMessage,
  isDuplicateDocumentError,
} from './errorHandler'

describe('duplicate document error mapping', () => {
  it('recognises DUPLICATE_DOCUMENT from Axios responses', () => {
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
          detail: 'Annual_Report.pdf has already been uploaded.',
          code: 'DUPLICATE_DOCUMENT',
        },
      },
    )

    expect(isDuplicateDocumentError(error)).toBe(true)
    expect(getApiErrorMessage(error)).toBe(DUPLICATE_DOCUMENT_USER_MESSAGE)
    expect(getApiErrorMessage(error)).not.toBe('An unexpected error occurred.')
  })

  it('recognises DUPLICATE_DOCUMENT from rethrown ApiError objects', () => {
    const apiError = {
      message: 'Annual_Report.pdf has already been uploaded.',
      status: 409,
      code: 'DUPLICATE_DOCUMENT' as const,
    }

    expect(isDuplicateDocumentError(apiError)).toBe(true)
    expect(getApiErrorMessage(apiError)).toBe('This document has already been uploaded.')
  })

  it('does not treat other HTTP 409 responses as duplicates', () => {
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
          detail: 'Document integrity check failed.',
        },
      },
    )

    expect(isDuplicateDocumentError(error)).toBe(false)
    expect(getApiErrorMessage(error)).toBe('Document integrity check failed.')
  })
})
