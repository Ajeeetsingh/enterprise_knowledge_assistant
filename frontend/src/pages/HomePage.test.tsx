import { act, render, screen, waitFor } from '@testing-library/react'
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

  it('renders a clean hero hierarchy with demo and login CTAs', async () => {
    renderHome()

    await act(async () => {
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => resolve())
      })
    })

    await waitFor(() => {
      expect(
        screen.getByRole('heading', {
          name: /ask anything\. get answers from your organisation's knowledge\./i,
        }),
      ).toBeInTheDocument()
    })

    expect(
      screen.queryByText(/search policies, procedures, and institutional knowledge/i),
    ).not.toBeInTheDocument()

    const heroDemo = screen.getByRole('link', { name: /try knowra/i })
    expect(heroDemo).toHaveAttribute('href', '/demo')

    const demoLinks = screen.getAllByRole('link', { name: /try the demo/i })
    expect(demoLinks.length).toBeGreaterThan(0)
    expect(demoLinks.every((link) => link.getAttribute('href') === '/demo')).toBe(true)

    const signInLinks = screen.getAllByRole('link', { name: /sign in/i })
    expect(signInLinks.length).toBeGreaterThan(0)
    expect(signInLinks.every((link) => link.getAttribute('href') === '/login')).toBe(true)

    expect(screen.getByRole('heading', { name: /stop searching\. start asking\./i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /get started/i })).not.toBeInTheDocument()
  })

  it('shows how-it-works and access sections with real product capabilities', () => {
    renderHome()

    expect(screen.getByRole('heading', { name: /from upload to cited answer/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /knowledge stays inside the right roles/i })).toBeInTheDocument()
    expect(screen.getByText(/hybrid indexing/i)).toBeInTheDocument()
    expect(screen.getByText('Employee')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('keeps CTAs interactive above the decorative hero animation', () => {
    const { container } = renderHome()

    const heroDemo = screen.getByRole('link', { name: /try knowra/i })
    expect(heroDemo).toHaveAttribute('href', '/demo')
    expect(heroDemo.closest('.relative.z-10')).toBeTruthy()
    expect(container.querySelector('.landing-page')).toBeTruthy()
    expect(container.querySelector('.landing-aura')).toBeTruthy()
    expect(container.querySelector('.hero-knowledge-anim')).toBeTruthy()
    expect(container.querySelector('.hero-aurora-layer--waves')).toBeTruthy()
    expect(container.querySelector('.hero-aurora-layer--network')).toBeTruthy()
  })

  it('shows the documents-to-answer knowledge flow in the hero', () => {
    renderHome()

    expect(screen.queryByLabelText('Product preview')).not.toBeInTheDocument()
    expect(screen.getByText('HR Policy')).toBeInTheDocument()
    expect(screen.getByText('Remote Work Policy')).toBeInTheDocument()
    expect(screen.getByText('Employee Handbook')).toBeInTheDocument()
    expect(
      screen.getByText(/employees may work remotely according to the approved hybrid-work guidelines/i),
    ).toBeInTheDocument()
    expect(screen.getByText('[1] HR Policy')).toBeInTheDocument()
    expect(screen.getByText('[2] Handbook')).toBeInTheDocument()
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
    expect(screen.queryByRole('link', { name: /try the demo/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /try knowra/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /get started/i })).not.toBeInTheDocument()
  })

  it('keeps development tools behind a Dev tools control in development', async () => {
    const user = userEvent.setup()
    renderHome()

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
