import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'

import UserMenu from './UserMenu'

const mockNavigate = vi.fn()
const mockLogout = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

const testUser = {
  id: '1',
  email: 'admin@example.com',
  full_name: 'Admin User',
  roles: ['Admin'],
  is_active: true,
  is_superuser: false,
}

function renderUserMenu() {
  return render(
    <MemoryRouter>
      <UserMenu />
    </MemoryRouter>,
  )
}

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLogout.mockResolvedValue(undefined)
    mockUseAuth.mockReturnValue({
      user: testUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      refreshUser: vi.fn(),
    })
  })

  it('opens the menu and shows user details', async () => {
    const user = userEvent.setup()
    renderUserMenu()

    await user.click(screen.getByRole('button', { name: /user menu for admin user/i }))

    expect(screen.getByRole('menu', { name: /user account menu/i })).toBeInTheDocument()
    expect(screen.getAllByText('Admin User').length).toBeGreaterThan(0)
    expect(screen.getAllByText('admin@example.com').length).toBeGreaterThan(0)
    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /my profile/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /logout/i })).toBeInTheDocument()
  })

  it('closes when clicking outside', async () => {
    const user = userEvent.setup()
    renderUserMenu()

    await user.click(screen.getByRole('button', { name: /user menu for admin user/i }))
    expect(screen.getByRole('menu')).toBeInTheDocument()

    await user.click(document.body)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('closes when pressing Escape', async () => {
    const user = userEvent.setup()
    renderUserMenu()

    await user.click(screen.getByRole('button', { name: /user menu for admin user/i }))
    expect(screen.getByRole('menu')).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('navigates to profile from the menu', async () => {
    const user = userEvent.setup()
    renderUserMenu()

    await user.click(screen.getByRole('button', { name: /user menu for admin user/i }))
    await user.click(screen.getByRole('menuitem', { name: /my profile/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/profile')
  })

  it('logs out and redirects to login', async () => {
    const user = userEvent.setup()
    renderUserMenu()

    await user.click(screen.getByRole('button', { name: /user menu for admin user/i }))
    await user.click(screen.getByRole('menuitem', { name: /logout/i }))

    expect(mockLogout).toHaveBeenCalledTimes(1)
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })
})
