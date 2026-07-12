import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
}))

import apiClient from '@/services/api'
import { UPLOAD_REQUEST_TIMEOUT_MS } from '../constants'
import { uploadDocument } from '../services/documentApi'

describe('uploadDocument', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset()
  })

  it('uses an extended timeout for synchronous ingestion', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        document_id: 'doc-1',
        filename: 'policy.pdf',
        status: 'searchable',
        message: 'ready',
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    })

    const file = new File(['content'], 'policy.pdf', { type: 'application/pdf' })
    await uploadDocument(file)

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents/upload',
      expect.any(FormData),
      { timeout: UPLOAD_REQUEST_TIMEOUT_MS },
    )
    expect(UPLOAD_REQUEST_TIMEOUT_MS).toBeGreaterThan(30_000)
  })
})
