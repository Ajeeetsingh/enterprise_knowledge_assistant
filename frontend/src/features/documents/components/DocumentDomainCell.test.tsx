import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Document } from '../types'
import DocumentDomainCell from './DocumentDomainCell'

const DOMAINS = [
  { id: 'finance-id', name: 'Finance', description: null },
  { id: 'hr-id', name: 'Human Resources', description: null },
]

function makeDocument(overrides: Partial<Document> = {}): Document {
  return {
    document_id: 'doc-1',
    filename: 'Expense Policy.pdf',
    status: 'searchable',
    uploaded_at: '2026-01-01T00:00:00Z',
    uploaded_by: 'admin',
    domain_id: null,
    domain_name: null,
    ...overrides,
  }
}

describe('DocumentDomainCell', () => {
  it('shows read-only domain for non-admin users', () => {
    render(
      <DocumentDomainCell
        document={makeDocument({ domain_name: 'Finance', domain_id: 'finance-id' })}
        domains={DOMAINS}
        canEdit={false}
      />,
    )

    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('shows editable domain control for admins with existing domains', () => {
    render(
      <DocumentDomainCell
        document={makeDocument()}
        domains={[
          ...DOMAINS,
          { id: 'proc-id', name: 'Procurement', description: null },
        ]}
        canEdit
        onDomainChange={vi.fn()}
      />,
    )

    const select = screen.getByLabelText('Domain for Expense Policy.pdf')
    expect(select).toBeInTheDocument()
    expect(select).toHaveValue('')
    expect(screen.getByRole('option', { name: 'Uncategorized' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Finance' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Human Resources' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Procurement' })).toBeInTheDocument()
  })

  it('calls onDomainChange when Admin selects Finance', async () => {
    const user = userEvent.setup()
    const onDomainChange = vi.fn().mockResolvedValue(undefined)

    render(
      <DocumentDomainCell
        document={makeDocument()}
        domains={DOMAINS}
        canEdit
        onDomainChange={onDomainChange}
      />,
    )

    await user.selectOptions(
      screen.getByLabelText('Domain for Expense Policy.pdf'),
      'finance-id',
    )

    await waitFor(() => {
      expect(onDomainChange).toHaveBeenCalledWith(
        expect.objectContaining({ document_id: 'doc-1' }),
        'finance-id',
      )
    })
  })

  it('reverts the select value when the API fails', async () => {
    const user = userEvent.setup()
    const onDomainChange = vi.fn().mockRejectedValue(new Error('Denied'))

    render(
      <DocumentDomainCell
        document={makeDocument({ domain_id: null, domain_name: null })}
        domains={DOMAINS}
        canEdit
        onDomainChange={onDomainChange}
      />,
    )

    const select = screen.getByLabelText('Domain for Expense Policy.pdf')
    await user.selectOptions(select, 'finance-id')

    await waitFor(() => {
      expect(select).toHaveValue('')
    })
  })
})
