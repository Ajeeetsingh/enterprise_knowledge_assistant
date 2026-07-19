import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'

import LoginPage from './LoginPage'

const mockNavigate = vi.fn()
const mockLogin = vi.fn()

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

function renderLoginPage(initialEntries: string[] = ['/login']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: mockLogin,
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })
  })

  it('submits credentials and redirects on success', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValue(undefined)
    renderLoginPage()

    await user.type(screen.getByLabelText(/email address/i), 'admin@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'Secret123!')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'admin@example.com',
        password: 'Secret123!',
      })
    })
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
  })

  it('shows an invalid-credentials message on 401', async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValue({ message: 'Invalid credentials', status: 401 })
    renderLoginPage()

    await user.type(screen.getByLabelText(/email address/i), 'admin@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('shows field validation errors for empty input', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByText('Email is required.')).toBeInTheDocument()
    expect(screen.getByText('Password is required.')).toBeInTheDocument()
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('links to the registration page', () => {
    renderLoginPage()
    expect(screen.getByRole('link', { name: /create an account/i })).toHaveAttribute(
      'href',
      '/register',
    )
  })
})
