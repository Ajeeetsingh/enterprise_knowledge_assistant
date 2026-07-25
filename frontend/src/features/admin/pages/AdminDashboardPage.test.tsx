import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import AdminDashboardPage from '../pages/AdminDashboardPage'

const useResourceMetrics = vi.fn()
const useSystemMonitoring = vi.fn()

vi.mock('@/features/analytics/hooks', () => ({
  useResourceMetrics: () => useResourceMetrics(),
  useSystemMonitoring: () => useSystemMonitoring(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminDashboardPage', () => {
  it('renders live metrics and scannable health + quick actions', () => {
    useResourceMetrics.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        total_documents: 7,
        total_users: 3,
        total_conversations: 11,
        storage_usage_bytes: 1536,
        vector_index_size_bytes: null,
        uploaded_file_count: 7,
        start_date: '2026-06-20T00:00:00Z',
        end_date: '2026-06-27T23:59:59Z',
      },
    })
    useSystemMonitoring.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        api_health: 'healthy',
        database_health: 'degraded',
        search_service_health: 'healthy',
        vector_index_health: 'healthy',
        overall_system_status: 'degraded',
        uptime_seconds: 120,
        version: '0.1.0',
        start_date: '2026-06-20T00:00:00Z',
        end_date: '2026-06-27T23:59:59Z',
      },
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Administration Dashboard' })).toBeInTheDocument()
    expect(screen.getByLabelText('Total Users: 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Total Documents: 7')).toBeInTheDocument()
    expect(screen.getByLabelText('Total Conversations: 11')).toBeInTheDocument()
    expect(screen.getByLabelText('Storage Usage: 1.5 KB')).toBeInTheDocument()

    expect(screen.getByLabelText('API: Healthy')).toBeInTheDocument()
    expect(screen.getByLabelText('Database: Degraded')).toBeInTheDocument()
    expect(screen.getByLabelText('Search: Healthy')).toBeInTheDocument()

    expect(
      screen.getByRole('link', { name: /View system monitoring/i }),
    ).toHaveAttribute('href', '/admin/analytics/monitoring')

    expect(screen.getByRole('heading', { name: 'Quick actions' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Manage users/i })).toHaveAttribute(
      'href',
      '/admin/users',
    )
    expect(screen.getByRole('link', { name: /Manage documents/i })).toHaveAttribute(
      'href',
      '/admin/documents',
    )
    expect(screen.getByRole('link', { name: /User analytics/i })).toHaveAttribute(
      'href',
      '/admin/analytics',
    )
    expect(screen.getByRole('link', { name: /AI analytics/i })).toHaveAttribute(
      'href',
      '/admin/analytics/ai',
    )
    expect(screen.getByRole('link', { name: /Knowledge analytics/i })).toHaveAttribute(
      'href',
      '/admin/analytics/knowledge',
    )

    expect(screen.queryByText(/placeholders until analytics/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/128/)).not.toBeInTheDocument()
  })

  it('shows loading skeletons while resources and health load', () => {
    useResourceMetrics.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    })
    useSystemMonitoring.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    })

    renderPage()

    expect(screen.getByLabelText('Total Users: Loading')).toBeInTheDocument()
    expect(screen.getByLabelText('API: Loading')).toBeInTheDocument()
    expect(screen.getByLabelText('Database: Loading')).toBeInTheDocument()
    expect(screen.getByLabelText('Search: Loading')).toBeInTheDocument()
    expect(screen.getByLabelText('System health: Loading')).toBeInTheDocument()
  })

  it('shows unavailable health when monitoring fails without crashing', () => {
    useResourceMetrics.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      error: new Error('boom'),
    })
    useSystemMonitoring.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    })

    renderPage()

    expect(screen.getByLabelText('Total Users: Unavailable')).toBeInTheDocument()
    expect(screen.getByLabelText('API: Unavailable')).toBeInTheDocument()
    expect(screen.getByLabelText('Database: Unavailable')).toBeInTheDocument()
    expect(screen.getByLabelText('Search: Unavailable')).toBeInTheDocument()
    expect(screen.getByLabelText('System health: Unavailable')).toBeInTheDocument()
    expect(screen.queryByText(/^Healthy$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Administration Dashboard' })).toBeInTheDocument()
  })
})
