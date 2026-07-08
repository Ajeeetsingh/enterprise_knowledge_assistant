import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Role } from '@/types/permissions'

import UserDetailsModal from './UserDetailsModal'
import { mockAdminUsers } from '../test/userFixtures'

describe('UserDetailsModal', () => {
  it('opens and displays user metadata', () => {
    render(
      <UserDetailsModal
        isOpen
        user={mockAdminUsers[0]!}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('dialog', { name: 'User Details' })).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('john@company.com')).toBeInTheDocument()
    expect(screen.getByText(Role.Admin)).toBeInTheDocument()
  })
})
