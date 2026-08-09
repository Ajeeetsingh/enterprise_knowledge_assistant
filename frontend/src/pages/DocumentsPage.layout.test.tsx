import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
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
      data: [{ id: 'finance-id', name: 'Finance', description: null }],
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

vi.mock('@/features/documents/hooks/useUpdateDocumentDomain', () => ({
  useUpdateDocumentDomain: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
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
      <MemoryRouter initialEntries={['/documents']}>
        <Routes>
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DocumentsPage layout scroll region', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
    } as ReturnType<typeof useAuth>)

    mockUseDocuments.mockReturnValue({
      data: {
        items: Array.from({ length: 8 }, (_, index) => ({
          document_id: `doc-${index}`,
          filename: `file-${index}.pdf`,
          status: 'searchable',
          uploaded_at: '2026-01-01T00:00:00Z',
          uploaded_by: 'user-1',
          domain_id: 'finance-id',
          domain_name: 'Finance',
        })),
        total: 8,
        limit: 50,
        offset: 0,
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useDocuments>)
  })

  it('keeps search and domain filters outside the table scrollport', () => {
    renderPage()
    const scroll = screen.getByTestId('document-table-scroll')
    expect(scroll.contains(screen.getByLabelText(/search/i))).toBe(false)
    expect(scroll.contains(screen.getByLabelText(/domain/i))).toBe(false)
  })
})
