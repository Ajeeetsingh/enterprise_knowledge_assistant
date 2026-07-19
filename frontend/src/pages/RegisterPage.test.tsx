import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/services/authApi'
import RegisterPage from '@/pages/RegisterPage'

vi.mock('@/services/authApi', () => ({
  register: vi.fn(),
}))

const mockRegister = vi.mocked(authApi.register)

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderRegister() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>,
  )
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders signup fields without a role selector', () => {
    renderRegister()

    expect(screen.getByRole('heading', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^role$/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /admin/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login')
  })

  it('validates required fields and password length', async () => {
    const user = userEvent.setup()
    renderRegister()

    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    expect(mockRegister).not.toHaveBeenCalled()

    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email address/i), 'ada@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'short')
    await user.type(screen.getByLabelText(/confirm password/i), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/at least 8 characters/i)
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('submits registration and redirects to login with success message', async () => {
    const user = userEvent.setup()
    mockRegister.mockResolvedValue({
      id: '1',
      email: 'ada@example.com',
      full_name: 'Ada Lovelace',
      message: 'Account created successfully. You can now sign in.',
    })

    renderRegister()

    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email address/i), 'ada@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'SecurePass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: 'ada@example.com',
        password: 'SecurePass1!',
        full_name: 'Ada Lovelace',
      })
    })

    expect(mockNavigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: {
        registrationSuccess: 'Account created successfully. You can now sign in.',
      },
    })
  })

  it('shows duplicate account errors', async () => {
    const user = userEvent.setup()
    mockRegister.mockRejectedValue({
      message: 'A user with this email already exists.',
      status: 409,
    })

    renderRegister()

    await user.type(screen.getByLabelText(/full name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/email address/i), 'ada@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'SecurePass1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'SecurePass1!')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /email already exists/i,
    )
  })
})
