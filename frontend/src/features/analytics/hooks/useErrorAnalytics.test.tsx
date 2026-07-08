import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as errorAnalyticsApi from '../services/errorAnalyticsApi'
import { useErrorAnalytics } from './useErrorAnalytics'

vi.mock('../services/errorAnalyticsApi', () => ({
  getErrorAnalyticsOverview: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useErrorAnalytics', () => {
  it('loads error overview metrics', async () => {
    vi.mocked(errorAnalyticsApi.getErrorAnalyticsOverview).mockResolvedValue({
      total_errors: 8,
      authentication_failures: 2,
      authorization_failures: 1,
      upload_failures: 0,
      indexing_failures: 0,
      retrieval_failures: 3,
      api_errors: null,
      background_job_failures: null,
      error_rate: 20,
      error_free_requests_percentage: 80,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    })

    const { result } = renderHook(() => useErrorAnalytics({ range_preset: 'last_7_days' }), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_errors).toBe(8)
  })
})
