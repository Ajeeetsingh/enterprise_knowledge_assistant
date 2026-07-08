import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as monitoringAnalyticsApi from '../services/monitoringAnalyticsApi'
import { useSystemMonitoring } from './useSystemMonitoring'

vi.mock('../services/monitoringAnalyticsApi', () => ({
  getSystemMonitoringOverview: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useSystemMonitoring', () => {
  it('loads system monitoring overview metrics', async () => {
    vi.mocked(monitoringAnalyticsApi.getSystemMonitoringOverview).mockResolvedValue({
      api_health: 'healthy',
      database_health: 'healthy',
      search_service_health: 'healthy',
      vector_index_health: 'healthy',
      overall_system_status: 'healthy',
      uptime_seconds: 120,
      version: '0.1.0',
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    })

    const { result } = renderHook(
      () => useSystemMonitoring({ range_preset: 'last_7_days' }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.overall_system_status).toBe('healthy')
  })
})
