import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DocumentFilters from './DocumentFilters'

describe('DocumentFilters', () => {
  it('updates search and filter values', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    const onSearchChange = vi.fn()

    render(
      <DocumentFilters
        filters={{ status: 'ALL', visibility: 'ALL' }}
        onChange={onChange}
        search=""
        onSearchChange={onSearchChange}
      />,
    )

    await user.type(screen.getByLabelText('Search documents'), 'handbook')
    expect(onSearchChange).toHaveBeenCalled()

    await user.selectOptions(screen.getByLabelText('Status'), 'READY')
    expect(onChange).toHaveBeenCalledWith({ status: 'READY', visibility: 'ALL' })

    await user.selectOptions(screen.getByLabelText('Visibility'), 'PUBLIC')
    expect(onChange).toHaveBeenCalledWith({ status: 'ALL', visibility: 'PUBLIC' })
  })
})
