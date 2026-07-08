import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DocumentDetailsModal from './DocumentDetailsModal'
import { DocumentStatus } from '@/features/documents/types'

const mockDetail = {
  document_id: 'doc-1',
  filename: 'Employee Handbook.pdf',
  content_type: 'application/pdf',
  file_size: 2048,
  checksum: 'abc123',
  status: DocumentStatus.Searchable,
  uploaded_at: '2026-06-01T10:00:00Z',
  uploaded_by: 'user-1',
}

describe('DocumentDetailsModal', () => {
  it('opens and displays metadata', () => {
    render(
      <DocumentDetailsModal
        isOpen
        documentDetail={mockDetail}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('dialog', { name: 'Document Details' })).toBeInTheDocument()
    expect(screen.getByText('Employee Handbook.pdf')).toBeInTheDocument()
    expect(screen.getByText('application/pdf')).toBeInTheDocument()
    expect(screen.getByText('abc123')).toBeInTheDocument()
  })

  it('renders error state with retry action', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <DocumentDetailsModal
        isOpen
        documentDetail={null}
        isLoading={false}
        error="Unable to load document details."
        onClose={vi.fn()}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load document details.')
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
