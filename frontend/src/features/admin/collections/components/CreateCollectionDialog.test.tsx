import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CreateCollectionDialog from './CreateCollectionDialog'

describe('CreateCollectionDialog', () => {
  it('opens create collection dialog', () => {
    render(
      <CreateCollectionDialog
        isOpen
        isSubmitting={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByRole('dialog', { name: 'Create Collection' })).toBeInTheDocument()
  })

  it('shows create error state', () => {
    render(
      <CreateCollectionDialog
        isOpen
        isSubmitting={false}
        error="Unable to create collection."
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to create collection.')
  })

  it('submits valid collection data', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(
      <CreateCollectionDialog
        isOpen
        isSubmitting={false}
        error={null}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    )

    await user.type(screen.getByLabelText('Collection name'), 'Legal')
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(onSubmit).toHaveBeenCalledWith({ name: 'Legal', description: '' })
  })
})
