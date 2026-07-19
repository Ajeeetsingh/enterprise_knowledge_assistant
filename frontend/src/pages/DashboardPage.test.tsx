import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'
import { useConversations } from '@/features/chat/hooks/useConversations'
import { useWorkspaceSummary } from '@/features/dashboard'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import DashboardPage from '@/pages/DashboardPage'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/features/dashboard/hooks/useWorkspaceSummary', () => ({
  useWorkspaceSummary: vi.fn(),
}))

vi.mock('@/features/chat/hooks/useConversations', () => ({
  useConversations: vi.fn(),
}))

vi.mock('@/features/documents/hooks/useDocuments', () => ({
  useDocuments: vi.fn(),
}))

vi.mock('@/features/monitoring/hooks', () => ({
  useMonitoringSummary: vi.fn(() => ({ data: undefined, isLoading: false })),
  useSystemMetrics: vi.fn(() => ({ data: undefined, isLoading: false })),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockUseWorkspaceSummary = vi.mocked(useWorkspaceSummary)
const mockUseConversations = vi.mocked(useConversations)
const mockUseDocuments = vi.mocked(useDocuments)

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        email: 'ada@example.com',
        full_name: 'Ada Lovelace',
        roles: ['Employee'],
        is_active: true,
        is_superuser: false,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })
    mockUseWorkspaceSummary.mockReturnValue({
      data: {
        documents_available: 2,
        conversations: 1,
        questions_asked: 3,
        collections: null,
      },
      isLoading: false,
    } as ReturnType<typeof useWorkspaceSummary>)
    mockUseConversations.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    } as ReturnType<typeof useConversations>)
    mockUseDocuments.mockReturnValue({
      data: { items: [], total: 0, limit: 10, offset: 0 },
      isLoading: false,
    } as ReturnType<typeof useDocuments>)
  })

  it('renders a personalized greeting and ask bar', () => {
    renderDashboard()

    expect(
      screen.getByRole('heading', { name: /good (morning|afternoon|evening), ada/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/your knowledge workspace is ready/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/ask anything/i)).toBeInTheDocument()
  })

  it('shows empty-state copy when there is no prior work', () => {
    renderDashboard()

    expect(
      screen.getByText(/you haven't asked anything yet — try the box above/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/no documents available yet/i),
    ).toBeInTheDocument()
  })

  it('hides analytics and upload actions for employees without create permission', () => {
    renderDashboard()

    expect(screen.getByRole('link', { name: /ask a question/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /browse knowledge/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /upload documents/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /view analytics/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /system overview/i })).not.toBeInTheDocument()
  })
})
