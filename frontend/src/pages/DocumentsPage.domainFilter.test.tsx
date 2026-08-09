import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import { useKnowledgeDomains } from '@/features/knowledge-domains'
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
    useKnowledgeDomains: vi.fn(),
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

vi.mock('@/features/documents/hooks/useUpdateDocumentDomain', () => ({
  useUpdateDocumentDomain: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
  }),
}))

const mockUseAuth = vi.mocked(useAuth)
const mockUseDocuments = vi.mocked(useDocuments)
const mockUseKnowledgeDomains = vi.mocked(useKnowledgeDomains)

const FINANCE_ID = '11111111-1111-1111-1111-111111111111'
const HR_ID = '22222222-2222-2222-2222-222222222222'

function renderPage(initialEntry = '/documents') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DocumentsPage domain filter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        email: 'admin@example.com',
        full_name: 'Admin',
        roles: ['Admin'],
        is_active: true,
        is_superuser: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })
    mockUseKnowledgeDomains.mockReturnValue({
      data: [
        { id: FINANCE_ID, name: 'Finance', description: null },
        { id: HR_ID, name: 'Human Resources', description: null },
      ],
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useKnowledgeDomains>)
    mockUseDocuments.mockReturnValue({
      data: {
        items: [
          {
            document_id: 'doc-1',
            filename: 'Budget FY2026.pdf',
            status: 'searchable',
            uploaded_at: '2026-01-01T00:00:00Z',
            uploaded_by: '1',
            domain_id: FINANCE_ID,
            domain_name: 'Finance',
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useDocuments>)
  })

  function getDomainFilter() {
    const filters = screen.getByRole('region', { name: 'Document filters' })
    return within(filters).getByLabelText('Domain')
  }

  it('preserves domain filter in the URL and requests filtered documents', () => {
    renderPage(`/documents?domain_id=${FINANCE_ID}`)
    expect(getDomainFilter()).toHaveValue(FINANCE_ID)
    expect(mockUseDocuments).toHaveBeenCalledWith(
      expect.objectContaining({ domain_id: FINANCE_ID, offset: 0 }),
    )
    expect(screen.getByText('Budget FY2026.pdf')).toBeInTheDocument()
  })

  it('combines search and domain filter in the documents request', async () => {
    const user = userEvent.setup()
    renderPage(`/documents?domain_id=${FINANCE_ID}`)

    await user.type(screen.getByLabelText('Search documents'), 'budget')

    await waitFor(() => {
      expect(mockUseDocuments).toHaveBeenCalledWith(
        expect.objectContaining({
          domain_id: FINANCE_ID,
          filename: 'budget',
        }),
      )
    })
  })

  it('shows a loading state while filtered results load', () => {
    mockUseDocuments.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      isError: false,
      error: null,
    } as ReturnType<typeof useDocuments>)

    renderPage(`/documents?domain_id=${FINANCE_ID}`)
    expect(screen.getByLabelText('Loading documents')).toBeInTheDocument()
  })

  it('shows a domain-specific empty state', () => {
    mockUseDocuments.mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useDocuments>)

    renderPage(`/documents?domain_id=${FINANCE_ID}`)
    expect(screen.getByText('No documents found in Finance.')).toBeInTheDocument()
  })
})
