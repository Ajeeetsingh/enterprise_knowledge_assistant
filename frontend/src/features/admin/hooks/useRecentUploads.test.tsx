import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as documentApi from '@/features/documents/services/documentApi'
import { DocumentStatus } from '@/features/documents/types'

import { useRecentUploads } from './useRecentUploads'

vi.mock('@/features/documents/services/documentApi', () => ({
  getDocuments: vi.fn(),
}))

const mockGetDocuments = vi.mocked(documentApi.getDocuments)

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useRecentUploads', () => {
  it('stops polling after unmount', async () => {
    mockGetDocuments.mockResolvedValue({
      items: [
        {
          document_id: 'doc-1',
          filename: 'Guide.pdf',
          status: DocumentStatus.Processing,
          uploaded_at: '2026-06-01T10:00:00Z',
          uploaded_by: 'user-1',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    })

    const { unmount } = renderHook(() => useRecentUploads(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(mockGetDocuments).toHaveBeenCalledTimes(1)
    })

    unmount()

    const callsAfterUnmount = mockGetDocuments.mock.calls.length
    await new Promise((resolve) => {
      window.setTimeout(resolve, 100)
    })

    expect(mockGetDocuments.mock.calls.length).toBe(callsAfterUnmount)
  })
})
