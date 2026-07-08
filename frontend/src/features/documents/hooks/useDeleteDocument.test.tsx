import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { PaginatedDocumentResponse } from '@/features/documents/types'
import { documentQueryKeys } from '@/features/documents/hooks/queryKeys'
import { useDeleteDocument } from '@/features/documents/hooks/useDeleteDocument'

vi.mock('@/features/documents/services/documentApi', () => ({
  deleteDocument: vi.fn(async (documentId: string) => ({
    document_id: documentId,
    status: 'deleted',
    message: 'Document deleted.',
  })),
}))

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useDeleteDocument', () => {
  it('removes deleted document from list cache on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const listKey = [...documentQueryKeys.list(), { limit: 50, offset: 0 }]
    const initial: PaginatedDocumentResponse = {
      items: [
        {
          document_id: 'doc-1',
          filename: 'keep.pdf',
          status: 'searchable',
          uploaded_at: '2026-01-01T00:00:00Z',
          uploaded_by: 'user-1',
        },
        {
          document_id: 'doc-2',
          filename: 'remove.pdf',
          status: 'processing',
          uploaded_at: '2026-01-02T00:00:00Z',
          uploaded_by: 'user-1',
        },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    }
    queryClient.setQueryData(listKey, initial)

    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: createWrapper(queryClient),
    })

    await result.current.mutateAsync('doc-2')

    await waitFor(() => {
      const cached = queryClient.getQueryData<PaginatedDocumentResponse>(listKey)
      expect(cached?.items).toHaveLength(1)
      expect(cached?.items[0]?.document_id).toBe('doc-1')
      expect(cached?.total).toBe(1)
    })
  })
})
