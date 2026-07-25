import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { GuestDemoPage } from '@/features/demo'
import * as chatApi from '@/features/chat/services/chatApi'
import * as demoApi from '@/features/demo/services/demoApi'
import {
  GUEST_POST_AUTH_PATH,
  GUEST_QUESTION_LIMIT,
  GUEST_STORAGE_KEY,
  GUEST_TRANSITION_KEY,
} from '@/features/demo/constants'
import { saveGuestSession } from '@/features/demo/storage/guestSessionStorage'
import { isGuestImportPending } from '@/features/demo/storage/guestTransitionStorage'
import { createGuestMessage } from '@/features/demo/types'

vi.mock('@/features/chat/services/chatApi', () => ({
  askQuestion: vi.fn(),
  getSuggestedQuestions: vi.fn(),
  getConversations: vi.fn(),
  createConversation: vi.fn(),
  importGuestConversation: vi.fn(),
}))

vi.mock('@/features/demo/services/demoApi', () => ({
  askGuestQuestion: vi.fn(),
}))

vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'light' as const,
    toggleTheme: vi.fn(),
    setTheme: vi.fn(),
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
    showInfo: vi.fn(),
    showWarning: vi.fn(),
  }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}))

vi.mock('@/hooks/useMinWidthMediaQuery', () => ({
  useMinWidthMediaQuery: () => true,
}))

const mockAskQuestion = vi.mocked(chatApi.askQuestion)
const mockAskGuest = vi.mocked(demoApi.askGuestQuestion)

function renderDemo() {
  return render(
    <MemoryRouter>
      <GuestDemoPage />
    </MemoryRouter>,
  )
}

function getComposer() {
  return screen.getByRole('textbox', { name: 'Message' })
}

describe('GuestDemoPage Phase 2/3', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    Element.prototype.scrollTo = vi.fn()
  })

  it('renders guest shell without private navigation', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: /guest chat/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /admin portal/i })).not.toBeInTheDocument()
  })

  it('Sign In preserves guest transition intent to /chat', async () => {
    const user = userEvent.setup()
    renderDemo()

    const signInLinks = screen.getAllByRole('link', { name: /^sign in$/i })
    const headerSignIn = signInLinks.find((link) => link.getAttribute('href') === '/login')
    expect(headerSignIn).toBeTruthy()
    await user.click(headerSignIn!)

    expect(isGuestImportPending()).toBe(true)
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeTruthy()
    expect(headerSignIn).toHaveAttribute('href', '/login')
    // React Router state is not readable from href; verify intent target constant.
    expect(GUEST_POST_AUTH_PATH).toBe('/chat')
  })

  it('calls public demo API and never authenticated chat APIs', async () => {
    mockAskGuest.mockResolvedValue({
      answer: 'I am Knowra.',
      confidence_score: 1,
      message: 'ok',
      answer_kind: 'product_help',
      requires_auth: false,
    })
    const user = userEvent.setup()
    renderDemo()

    await user.click(
      screen.getByRole('button', { name: /what can this assistant help me with/i }),
    )

    await waitFor(() => {
      expect(screen.getByText('I am Knowra.')).toBeInTheDocument()
    })
    expect(mockAskGuest).toHaveBeenCalledTimes(1)
    expect(mockAskQuestion).not.toHaveBeenCalled()
  })

  it('restores guest messages from sessionStorage after remount', () => {
    saveGuestSession({
      version: 1,
      messages: [
        createGuestMessage('user', 'What is RAG?'),
        createGuestMessage('assistant', 'RAG stands for retrieval-augmented generation.'),
      ],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })

    renderDemo()

    expect(screen.getByText('What is RAG?')).toBeInTheDocument()
    expect(
      screen.getByText('RAG stands for retrieval-augmented generation.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/questions remaining/i).textContent).toMatch(/9 of 10/)
  })

  it('shows Sign In when document answers require authentication', async () => {
    mockAskGuest.mockResolvedValue({
      answer:
        "I can answer questions from your organisation's documents once you're signed in and have access to them. Sign in to continue with document-based questions.",
      confidence_score: 0.9,
      message: 'auth',
      answer_kind: 'guest_auth_required',
      requires_auth: true,
    })
    const user = userEvent.setup()
    renderDemo()

    await user.type(getComposer(), 'What is our leave policy?')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(screen.getByText(/once you're signed in/i)).toBeInTheDocument()
    })
    const signInLinks = screen.getAllByRole('link', { name: /^sign in$/i })
    expect(signInLinks.some((link) => link.getAttribute('href') === '/login')).toBe(true)
  })

  it('restores question count from sessionStorage and blocks at the limit', () => {
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'prior')],
      successfulQuestionCount: GUEST_QUESTION_LIMIT,
      updatedAt: new Date().toISOString(),
    })

    renderDemo()

    expect(screen.getByText(/you've reached the guest demo limit/i)).toBeInTheDocument()
    const banner = screen.getByText(/you've reached the guest demo limit/i).closest('div')
    expect(banner).toBeTruthy()
    expect(within(banner as HTMLElement).getByRole('link', { name: /^sign in$/i })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(
      within(banner as HTMLElement).getByRole('link', { name: /create account/i }),
    ).toHaveAttribute('href', '/register')
    expect(mockAskGuest).not.toHaveBeenCalled()
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeTruthy()
    expect(getComposer()).toBeDisabled()
  })

  it('does not consume the limit when the demo API fails', async () => {
    mockAskGuest.mockRejectedValue(new Error('network down'))
    const user = userEvent.setup()
    renderDemo()

    await user.type(getComposer(), 'Explain EBITDA')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(screen.getByText(/questions remaining/i).textContent).toMatch(/10 of 10/)
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})
