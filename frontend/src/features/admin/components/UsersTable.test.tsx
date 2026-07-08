import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import UsersTable from './UsersTable'
import { mockAdminUsers } from '../test/userFixtures'

describe('UsersTable', () => {
  it('renders user rows', () => {
    render(
      <UsersTable
        users={mockAdminUsers}
        isLoading={false}
        onView={vi.fn()}
        onManageRole={vi.fn()}
        onToggleStatus={vi.fn()}
      />,
    )

    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('jane@company.com')).toBeInTheDocument()
    expect(screen.getByText('Disabled')).toBeInTheDocument()
  })

  it('blocks self-disable action', () => {
    render(
      <UsersTable
        users={[mockAdminUsers[0]!]}
        isLoading={false}
        currentUserId="user-1"
        onView={vi.fn()}
        onManageRole={vi.fn()}
        onToggleStatus={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Disable' })).toBeDisabled()
  })
})
