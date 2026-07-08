import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'john@company.com',
      full_name: 'John Doe',
      roles: ['Admin'],
      is_active: true,
      is_superuser: false,
    },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}))

import UserRoleSelector from './UserRoleSelector'
import { mockAdminUsers } from '../test/userFixtures'

const roles = [
  {
    id: 1,
    name: 'Admin',
    description: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Employee',
    description: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

describe('UserRoleSelector', () => {
  it('runs role update confirmation flow', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <UserRoleSelector
        user={mockAdminUsers[1]!}
        roles={roles}
        isOpen
        isUpdating={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    )

    await user.selectOptions(screen.getByLabelText('Role'), 'Admin')
    await user.click(screen.getByRole('button', { name: 'Apply' }))
    expect(screen.getByText('Confirm role change?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onConfirm).toHaveBeenCalledWith('Admin')
  })
})
