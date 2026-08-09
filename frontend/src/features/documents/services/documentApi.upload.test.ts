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
    await uploadDocument(file, 'domain-1')

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents/upload',
      expect.any(FormData),
      { timeout: UPLOAD_REQUEST_TIMEOUT_MS },
    )
    const formData = vi.mocked(apiClient.post).mock.calls[0]![1] as FormData
    expect(formData.get('file')).toBe(file)
    expect(formData.get('domain_id')).toBe('domain-1')
    expect(UPLOAD_REQUEST_TIMEOUT_MS).toBeGreaterThan(30_000)
  })
})
