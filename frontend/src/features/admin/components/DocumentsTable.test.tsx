import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DocumentsTable from './DocumentsTable'
import { mockAdminDocuments } from '../test/documentFixtures'

describe('DocumentsTable', () => {
  it('renders document rows', () => {
    render(
      <DocumentsTable
        documents={mockAdminDocuments}
        isLoading={false}
        onView={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText('Employee Handbook.pdf')).toBeInTheDocument()
    expect(screen.getByText('Finance Policy.pdf')).toBeInTheDocument()
    expect(screen.getByText('HR Notes.txt')).toBeInTheDocument()
  })

  it('opens view and delete actions', async () => {
    const user = userEvent.setup()
    const onView = vi.fn()
    const onDelete = vi.fn()

    render(
      <DocumentsTable
        documents={[mockAdminDocuments[0]!]}
        isLoading={false}
        onView={onView}
        onDelete={onDelete}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'View' }))
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onView).toHaveBeenCalledWith(mockAdminDocuments[0])
    expect(onDelete).toHaveBeenCalledWith(mockAdminDocuments[0])
  })
})
