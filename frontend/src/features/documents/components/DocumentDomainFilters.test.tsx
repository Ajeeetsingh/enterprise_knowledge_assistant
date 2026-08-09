import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DocumentDomainFilters, { ALL_DOMAINS_VALUE } from './DocumentDomainFilters'

const DOMAINS = [
  { id: 'finance-id', name: 'Finance', description: null },
  { id: 'hr-id', name: 'Human Resources', description: null },
]

describe('DocumentDomainFilters', () => {
  it('loads domain options and defaults to All Domains', () => {
    render(
      <DocumentDomainFilters
        search=""
        onSearchChange={vi.fn()}
        domainId={ALL_DOMAINS_VALUE}
        onDomainChange={vi.fn()}
        domains={DOMAINS}
      />,
    )

    const domainSelect = screen.getByLabelText('Domain')
    expect(domainSelect).toHaveValue(ALL_DOMAINS_VALUE)
    expect(screen.getByRole('option', { name: 'All Domains' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Finance' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Human Resources' })).toBeInTheDocument()
  })

  it('notifies when Finance is selected', async () => {
    const user = userEvent.setup()
    const onDomainChange = vi.fn()

    render(
      <DocumentDomainFilters
        search=""
        onSearchChange={vi.fn()}
        domainId={ALL_DOMAINS_VALUE}
        onDomainChange={onDomainChange}
        domains={DOMAINS}
      />,
    )

    await user.selectOptions(screen.getByLabelText('Domain'), 'finance-id')
    expect(onDomainChange).toHaveBeenCalledWith('finance-id')
  })
})
