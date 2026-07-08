import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import * as reportsApi from '../services/reportsApi'
import { useExportReport } from './useExportReport'

vi.mock('../services/reportsApi', () => ({
  exportReport: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useExportReport', () => {
  it('returns exported blob data', async () => {
    vi.mocked(reportsApi.exportReport).mockResolvedValue({
      blob: new Blob(['report']),
      filename: 'user_analytics_20260601_20260624.csv',
    })

    const { result } = renderHook(() => useExportReport(), {
      wrapper: createWrapper(),
    })

    await result.current.mutateAsync({
      module: 'user',
      format: 'csv',
      date_range: 'last_7_days',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.filename).toBe('user_analytics_20260601_20260624.csv')
  })
})
