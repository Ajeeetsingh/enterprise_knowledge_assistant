import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as aiAnalyticsApi from '../services/aiAnalyticsApi'
import { useAIAnalytics } from './useAIAnalytics'

vi.mock('../services/aiAnalyticsApi', () => ({
  getAIAnalyticsOverview: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useAIAnalytics', () => {
  it('loads AI overview metrics', async () => {
    vi.mocked(aiAnalyticsApi.getAIAnalyticsOverview).mockResolvedValue({
      total_questions: 5,
      responses_generated: 4,
      average_response_time_seconds: 1.8,
      average_retrieval_time_seconds: null,
      average_retrieved_documents: 2,
      citation_usage_rate: 75,
      retrieval_success_rate: 80,
      retrieval_failure_rate: 20,
      ai_error_rate: 20,
      average_confidence_score: 0.9,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    })

    const { result } = renderHook(() => useAIAnalytics({ range_preset: 'last_7_days' }), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_questions).toBe(5)
  })
})
