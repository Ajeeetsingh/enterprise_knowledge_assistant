import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as userAnalyticsApi from '../services/userAnalyticsApi'
import { useUserAnalytics } from './useUserAnalytics'

vi.mock('../services/userAnalyticsApi', () => ({
  getUserAnalyticsOverview: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useUserAnalytics', () => {
  it('loads overview metrics', async () => {
    vi.mocked(userAnalyticsApi.getUserAnalyticsOverview).mockResolvedValue({
      total_users: 10,
      new_users: 2,
      daily_active_users: 4,
      weekly_active_users: 6,
      monthly_active_users: 8,
      active_user_percentage: 40,
      average_conversations_per_user: 1.5,
      average_questions_per_user: 3.2,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    })

    const { result } = renderHook(() => useUserAnalytics({ range_preset: 'last_7_days' }), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_users).toBe(10)
  })
})
