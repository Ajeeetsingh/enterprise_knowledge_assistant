import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/contexts/AuthContext'
import HomePage from '@/pages/HomePage'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

describe('HomePage landing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })
  })

  it('renders the hero headline and public CTAs to register and login', () => {
    renderHome()

    expect(
      screen.getByRole('heading', {
        name: /ask anything\. get answers from your organisation's knowledge\./i,
      }),
    ).toBeInTheDocument()

    const getStartedLinks = screen.getAllByRole('link', { name: /get started/i })
    expect(getStartedLinks.length).toBeGreaterThan(0)
    expect(getStartedLinks[0]).toHaveAttribute('href', '/register')

    const signInLinks = screen.getAllByRole('link', { name: /sign in/i })
    expect(signInLinks.length).toBeGreaterThan(0)
    expect(signInLinks[0]).toHaveAttribute('href', '/login')
  })

  it('shows a grounded product preview with example citations', () => {
    renderHome()

    expect(screen.getByLabelText('Product preview')).toBeInTheDocument()
    expect(screen.getByText(/what is our annual leave policy/i)).toBeInTheDocument()
    expect(screen.getByText(/20 days/i)).toBeInTheDocument()
    expect(screen.getByText('Employee Handbook.pdf')).toBeInTheDocument()
  })

  it('shows dashboard CTA when authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: '1',
        email: 'admin@example.com',
        full_name: 'Admin',
        roles: ['Admin'],
        is_active: true,
        is_superuser: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    })

    renderHome()

    const dashboardLinks = screen.getAllByRole('link', { name: /go to dashboard/i })
    expect(dashboardLinks[0]).toHaveAttribute('href', '/dashboard')
    expect(screen.queryByRole('link', { name: /get started/i })).not.toBeInTheDocument()
  })

  it('keeps development tools behind a Dev tools control in development', async () => {
    const user = userEvent.setup()
    renderHome()

    // Design-system / layout-preview must not appear as public nav items.
    expect(screen.queryByRole('link', { name: /design system/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /layout preview/i })).not.toBeInTheDocument()

    if (import.meta.env.DEV) {
      await user.click(screen.getByRole('button', { name: /dev tools/i }))
      expect(screen.getByRole('menuitem', { name: /design system/i })).toHaveAttribute(
        'href',
        '/design-system',
      )
    } else {
      expect(screen.queryByRole('button', { name: /dev tools/i })).not.toBeInTheDocument()
    }
  })
})
