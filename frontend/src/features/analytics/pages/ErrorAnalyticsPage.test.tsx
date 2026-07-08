import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ErrorAnalyticsPage from './ErrorAnalyticsPage'

vi.mock('../hooks', () => ({
  useErrorAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_errors: 12,
      authentication_failures: 3,
      authorization_failures: 2,
      upload_failures: 1,
      indexing_failures: 1,
      retrieval_failures: 4,
      api_errors: null,
      background_job_failures: null,
      error_rate: 18.5,
      error_free_requests_percentage: 81.5,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useErrorTrends: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_errors: { event_type: 'total_errors', points: { '2026-06-27': 4 } },
      authentication_failures: { event_type: 'auth.login.failed', points: {} },
      retrieval_failures: { event_type: 'chat.retrieval.failed', points: { '2026-06-27': 2 } },
      upload_failures: { event_type: 'upload_failures', points: {} },
      api_exceptions: { event_type: 'api_exceptions', points: {} },
      permission_denials: { event_type: 'security.permission.denied', points: {} },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useErrorCategories: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      by_category: { AUTH: 3, CHAT: 4 },
      by_service: { authentication: 3, ai_service: 4 },
      by_severity: null,
      recurring_errors: [],
      total_recurring_errors: 0,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useEndpointFailures: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: { items: [], total: 0, limit: 10, offset: 0, start_date: '', end_date: '' },
    refetch: vi.fn(),
  }),
  useFailureAnalysis: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      failed_operations: [],
      retrieval_failures: [],
      upload_failures: [],
      authentication_failures: [],
      total_failed_operations: 0,
      total_retrieval_failures: 0,
      total_upload_failures: 0,
      total_authentication_failures: 0,
      limit: 10,
      offset: 0,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
}))

describe('ErrorAnalyticsPage', () => {
  it('renders error analytics dashboard sections', () => {
    render(<ErrorAnalyticsPage />)

    expect(screen.getByRole('heading', { name: 'Error Analytics' })).toBeInTheDocument()
    expect(screen.getByLabelText('Total Errors: 12')).toBeInTheDocument()
    expect(screen.getByText('Endpoint Failures')).toBeInTheDocument()
  })
})
