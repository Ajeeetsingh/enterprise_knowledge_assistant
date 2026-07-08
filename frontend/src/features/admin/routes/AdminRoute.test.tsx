import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'

import AdminRoute from '../routes/AdminRoute'
import { adminUser, employeeUser } from '../test/fixtures'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

function renderAdminRoute(initialRoute = '/admin') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <div>Admin Content</div>
            </AdminRoute>
          }
        />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/unauthorized" element={<div>Access Denied Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('allows authenticated admin users', () => {
    mockUseAuth.mockReturnValue({
      user: adminUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderAdminRoute()

    expect(screen.getByText('Admin Content')).toBeInTheDocument()
  })

  it('denies authenticated non-admin users', () => {
    mockUseAuth.mockReturnValue({
      user: employeeUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderAdminRoute()

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    expect(screen.getByText('Access Denied Page')).toBeInTheDocument()
  })

  it('redirects unauthenticated users to login', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderAdminRoute()

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })
})
