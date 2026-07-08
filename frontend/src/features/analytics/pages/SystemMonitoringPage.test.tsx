import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import SystemMonitoringPage from './SystemMonitoringPage'

vi.mock('../hooks', () => ({
  useSystemMonitoring: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      api_health: 'healthy',
      database_health: 'healthy',
      search_service_health: 'degraded',
      vector_index_health: 'healthy',
      overall_system_status: 'degraded',
      uptime_seconds: 3600,
      version: '0.1.0',
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  usePerformanceMetrics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      average_api_response_time_seconds: null,
      average_search_time_seconds: 2.1,
      average_retrieval_time_seconds: null,
      database_query_time_seconds: 0.002,
      embedding_generation_time_seconds: null,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useResourceMetrics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_documents: 12,
      total_users: 8,
      total_conversations: 20,
      storage_usage_bytes: 4096,
      vector_index_size_bytes: null,
      uploaded_file_count: 12,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useServiceStatus: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      items: [
        {
          service: 'database',
          status: 'healthy',
          detail: 'Database connectivity probe succeeded.',
        },
      ],
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useMonitoringTrends: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      api_latency: { event_type: 'api_latency', points: {} },
      search_latency: { event_type: 'search_latency', points: { '2026-06-27': 2 } },
      errors: { event_type: 'chat.retrieval.failed', points: { '2026-06-27': 1 } },
      health_events: { event_type: 'health_events', points: { '2026-06-27': 3 } },
      timeline_items: [],
      timeline_total: 0,
      timeline_limit: 10,
      timeline_offset: 0,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useHealthTimeline: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
}))

describe('SystemMonitoringPage', () => {
  it('renders system monitoring dashboard sections', () => {
    render(<SystemMonitoringPage />)

    expect(screen.getByRole('heading', { name: 'System Monitoring' })).toBeInTheDocument()
    expect(screen.getByText('API Health')).toBeInTheDocument()
    expect(screen.getByText('Resource Usage')).toBeInTheDocument()
    expect(screen.getByText('Service Status')).toBeInTheDocument()
  })
})
