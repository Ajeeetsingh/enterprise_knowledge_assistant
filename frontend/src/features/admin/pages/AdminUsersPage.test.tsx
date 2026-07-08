import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AdminUsersPage from './AdminUsersPage'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'admin@example.com',
      full_name: 'Admin User',
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

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
}))

vi.mock('@/features/users/hooks', () => ({
  useUsers: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    isError: true,
    error: { message: 'Unable to load users.' },
    refetch: vi.fn(),
  })),
  useUser: vi.fn(() => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useRoles: vi.fn(() => ({ data: { roles: [] } })),
  useUpdateUserRole: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useToggleUserStatus: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

describe('AdminUsersPage', () => {
  it('renders error state with retry action', () => {
    render(<AdminUsersPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load users.')
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
