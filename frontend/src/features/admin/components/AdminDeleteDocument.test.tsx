import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DeleteDocumentDialog from '@/features/documents/components/DeleteDocumentDialog'
import { mockAdminDocuments } from '../test/documentFixtures'

describe('Admin delete workflow', () => {
  it('opens delete confirmation dialog', () => {
    render(
      <DeleteDocumentDialog
        targetDocument={mockAdminDocuments[0]!}
        isOpen
        isDeleting={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    expect(screen.getByRole('alertdialog', { name: 'Delete document?' })).toBeInTheDocument()
    expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument()
  })

  it('calls confirm handler on delete success flow', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <DeleteDocumentDialog
        targetDocument={mockAdminDocuments[0]!}
        isOpen
        isDeleting={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
