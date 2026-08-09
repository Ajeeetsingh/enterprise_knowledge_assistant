import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import { useUpdateDocumentDomain } from '@/features/documents/hooks/useUpdateDocumentDomain'
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

vi.mock('@/features/documents/hooks/useUpdateDocumentDomain', () => ({
  useUpdateDocumentDomain: vi.fn(),
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

const mockUseAuth = vi.mocked(useAuth)
const mockUseDocuments = vi.mocked(useDocuments)
const mockUseKnowledgeDomains = vi.mocked(useKnowledgeDomains)
const mockUseUpdateDocumentDomain = vi.mocked(useUpdateDocumentDomain)

const FINANCE_ID = '11111111-1111-1111-1111-111111111111'

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

describe('DocumentsPage domain assignment', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseKnowledgeDomains.mockReturnValue({
      data: [
        { id: FINANCE_ID, name: 'Finance', description: null },
        {
          id: '22222222-2222-2222-2222-222222222222',
          name: 'Human Resources',
          description: null,
        },
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
            filename: 'Expense Policy.pdf',
            status: 'searchable',
            uploaded_at: '2026-01-01T00:00:00Z',
            uploaded_by: '1',
            domain_id: null,
            domain_name: null,
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
    mockUseUpdateDocumentDomain.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        document_id: 'doc-1',
        domain_id: FINANCE_ID,
        domain_name: 'Finance',
      }),
      isPending: false,
      variables: undefined,
    } as unknown as ReturnType<typeof useUpdateDocumentDomain>)
  })

  it('updates domain via mutation when Admin selects Finance', async () => {
    const user = userEvent.setup()
    const mutateAsync = vi.fn().mockResolvedValue({
      document_id: 'doc-1',
      domain_id: FINANCE_ID,
      domain_name: 'Finance',
    })
    mockUseUpdateDocumentDomain.mockReturnValue({
      mutateAsync,
      isPending: false,
      variables: undefined,
    } as unknown as ReturnType<typeof useUpdateDocumentDomain>)
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

    renderPage()
    await user.selectOptions(
      screen.getByLabelText('Domain for Expense Policy.pdf'),
      FINANCE_ID,
    )

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        documentId: 'doc-1',
        domainId: FINANCE_ID,
      })
    })
  })
})
