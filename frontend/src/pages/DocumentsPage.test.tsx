import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import DocumentsPage from '@/pages/DocumentsPage'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
}))

vi.mock('@/features/documents/hooks/useDocuments', () => ({
  useDocuments: vi.fn(),
}))

vi.mock('@/features/knowledge-domains', async () => {
  const actual = await vi.importActual<typeof import('@/features/knowledge-domains')>(
    '@/features/knowledge-domains',
  )
  return {
    ...actual,
    useKnowledgeDomains: () => ({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    }),
  }
})

vi.mock('@/features/documents/hooks/useUploadDocuments', () => ({
  useUploadDocuments: () => ({
    items: [],
    isUploading: false,
    uploadFiles: vi.fn(),
    retryFailed: vi.fn(),
    reset: vi.fn(),
  }),
  formatUploadBatchSummary: vi.fn(),
}))

vi.mock('@/features/documents/hooks/useDeleteDocument', () => ({
  useDeleteDocument: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockUseDocuments = vi.mocked(useDocuments)

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DocumentsPage upload permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseDocuments.mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useDocuments>)
  })

  it('shows upload controls for HR (document:create)', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        email: 'hr@example.com',
        full_name: 'HR User',
        roles: ['HR'],
        is_active: true,
        is_superuser: false,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderPage()
    expect(screen.getByRole('button', { name: 'Upload documents' })).toBeInTheDocument()
  })

  it('hides upload controls for Finance (no document:create)', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '2',
        email: 'finance@example.com',
        full_name: 'Finance User',
        roles: ['Finance'],
        is_active: true,
        is_superuser: false,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderPage()
    expect(screen.queryByRole('button', { name: 'Upload documents' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Upload your first document/i })).not.toBeInTheDocument()
  })
})
