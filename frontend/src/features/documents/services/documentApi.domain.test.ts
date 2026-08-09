import { beforeEach, describe, expect, it, vi } from 'vitest'

import apiClient from '@/services/api'

import { updateDocumentDomain } from './documentApi'

vi.mock('@/services/api', () => ({
  default: {
    patch: vi.fn(),
  },
}))

const mockPatch = vi.mocked(apiClient.patch)

describe('updateDocumentDomain', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPatch.mockResolvedValue({
      data: {
        document_id: 'doc-1',
        filename: 'policy.pdf',
        status: 'searchable',
        uploaded_at: '2026-01-01T00:00:00Z',
        uploaded_by: 'admin',
        domain_id: 'finance-id',
        domain_name: 'Finance',
      },
    })
  })

  it('PATCHes the document domain endpoint', async () => {
    const result = await updateDocumentDomain('doc-1', 'finance-id')
    expect(mockPatch).toHaveBeenCalledWith('/documents/doc-1/domain', {
      domain_id: 'finance-id',
    })
    expect(result.domain_name).toBe('Finance')
  })

  it('allows clearing the domain with null', async () => {
    mockPatch.mockResolvedValue({
      data: {
        document_id: 'doc-1',
        filename: 'policy.pdf',
        status: 'searchable',
        uploaded_at: '2026-01-01T00:00:00Z',
        uploaded_by: 'admin',
        domain_id: null,
        domain_name: null,
      },
    })
    await updateDocumentDomain('doc-1', null)
    expect(mockPatch).toHaveBeenCalledWith('/documents/doc-1/domain', {
      domain_id: null,
    })
  })
})
