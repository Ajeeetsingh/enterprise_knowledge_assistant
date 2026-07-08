import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AdminDocumentsPage from './AdminDocumentsPage'

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
}))

vi.mock('@/features/documents/hooks', () => ({
  useDocuments: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    isError: true,
    error: { message: 'Unable to load documents.' },
    refetch: vi.fn(),
  })),
  useDocument: vi.fn(() => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useDeleteDocument: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}))

describe('AdminDocumentsPage', () => {
  it('renders error state with retry action', () => {
    render(<AdminDocumentsPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load documents.')
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
