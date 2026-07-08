import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as knowledgeAnalyticsApi from '../services/knowledgeAnalyticsApi'
import { useKnowledgeAnalytics } from './useKnowledgeAnalytics'

vi.mock('../services/knowledgeAnalyticsApi', () => ({
  getKnowledgeAnalyticsOverview: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useKnowledgeAnalytics', () => {
  it('loads knowledge overview metrics', async () => {
    vi.mocked(knowledgeAnalyticsApi.getKnowledgeAnalyticsOverview).mockResolvedValue({
      total_documents: 12,
      active_documents: 10,
      stale_documents: 2,
      unused_documents: 4,
      average_document_views: 1.5,
      average_citations_per_document: 1.2,
      search_success_rate: 82,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    })

    const { result } = renderHook(
      () => useKnowledgeAnalytics({ range_preset: 'last_7_days' }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_documents).toBe(12)
  })
})
