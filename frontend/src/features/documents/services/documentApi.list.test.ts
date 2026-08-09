import { beforeEach, describe, expect, it, vi } from 'vitest'

import apiClient from '@/services/api'

import { getDocuments } from './documentApi'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

const mockGet = vi.mocked(apiClient.get)

describe('getDocuments domain filter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGet.mockResolvedValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
    })
  })

  it('omits domain_id when not provided', async () => {
    await getDocuments({ limit: 50, offset: 0 })
    expect(mockGet).toHaveBeenCalledWith('/documents', {
      params: { limit: 50, offset: 0 },
    })
  })

  it('includes domain_id and filename together', async () => {
    await getDocuments({
      limit: 20,
      offset: 0,
      domain_id: 'finance-id',
      filename: 'budget',
    })
    expect(mockGet).toHaveBeenCalledWith('/documents', {
      params: {
        limit: 20,
        offset: 0,
        filename: 'budget',
        domain_id: 'finance-id',
      },
    })
  })
})
