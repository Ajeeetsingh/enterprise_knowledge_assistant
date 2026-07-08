import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ToggleUserStatusDialog from './ToggleUserStatusDialog'
import { mockAdminUsers } from '../test/userFixtures'

describe('ToggleUserStatusDialog', () => {
  it('opens disable confirmation dialog', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <ToggleUserStatusDialog
        targetUser={mockAdminUsers[1]!}
        isOpen
        isSubmitting={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    )

    expect(screen.getByRole('alertdialog', { name: 'Enable user?' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Enable user' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('shows self-disable protection message', () => {
    render(
      <ToggleUserStatusDialog
        targetUser={mockAdminUsers[0]!}
        currentUserId="user-1"
        isOpen
        isSubmitting={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('You cannot disable your own account.')
    expect(screen.getByRole('button', { name: 'Disable user' })).toBeDisabled()
  })
})
