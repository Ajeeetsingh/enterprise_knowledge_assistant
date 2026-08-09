import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ChatPage from '@/pages/ChatPage'
import * as chatApi from '@/features/chat/services/chatApi'
import {
  GUEST_STORAGE_KEY,
  GUEST_TRANSITION_KEY,
  armGuestContinuePrompt,
  clearGuestImportPending,
  markGuestImportPending,
} from '@/features/demo'
import { saveGuestSession } from '@/features/demo/storage/guestSessionStorage'
import { createGuestMessage } from '@/features/demo/types'

vi.mock('@/features/chat/services/chatApi', () => ({
  getConversations: vi.fn(),
  createConversation: vi.fn(),
  askQuestion: vi.fn(),
  getMessages: vi.fn(),
  getSuggestedQuestions: vi.fn(),
  updateConversation: vi.fn(),
  deleteConversation: vi.fn(),
  importGuestConversation: vi.fn(),
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
    showInfo: vi.fn(),
    showWarning: vi.fn(),
  }),
}))

vi.mock('@/contexts/LayoutContext', () => ({
  useLayoutContext: () => ({
    setChatRouteActive: vi.fn(),
    closeConversationDrawer: vi.fn(),
    setMobileChatPanel: vi.fn(),
    conversationDrawerOpen: false,
  }),
}))

vi.mock('@/hooks/useMinWidthMediaQuery', () => ({
  useMinWidthMediaQuery: () => true,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useOutletContext: () => ({ sidebarWidth: 240, sidebarCollapsed: false }),
  }
})

const mockGetConversations = vi.mocked(chatApi.getConversations)
const mockImportGuest = vi.mocked(chatApi.importGuestConversation)
const mockAskQuestion = vi.mocked(chatApi.askQuestion)

function renderChat() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/chat']}>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function seedGuestConversation() {
  markGuestImportPending()
  saveGuestSession({
    version: 1,
    messages: [
      createGuestMessage('user', 'What is RAG?'),
      createGuestMessage('assistant', 'Retrieval-augmented generation.'),
    ],
    successfulQuestionCount: 1,
    updatedAt: new Date().toISOString(),
  })
}

describe('ChatPage guest continue prompt', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    Element.prototype.scrollTo = vi.fn()
    mockGetConversations.mockResolvedValue({ items: [], total: 0 })
  })

  it('does not show continue prompt without pending transition', () => {
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    renderChat()
    expect(screen.queryByText(/continue your guest conversation/i)).not.toBeInTheDocument()
    expect(mockImportGuest).not.toHaveBeenCalled()
  })

  it('does not show continue prompt for authenticated users with only stale guest storage', async () => {
    seedGuestConversation()
    renderChat()
    expect(screen.queryByText(/continue your guest conversation/i)).not.toBeInTheDocument()
    await waitFor(() => {
      expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeNull()
      expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeNull()
    })
  })

  it('shows continue prompt only when post-login ready flag is armed', () => {
    seedGuestConversation()
    armGuestContinuePrompt()
    renderChat()
    expect(screen.getByText(/continue your guest conversation/i)).toBeInTheDocument()
    expect(mockImportGuest).not.toHaveBeenCalled()
  })

  it('Start fresh clears guest state without import', async () => {
    seedGuestConversation()
    armGuestContinuePrompt()
    const user = userEvent.setup()
    renderChat()

    await user.click(screen.getByRole('button', { name: /start fresh/i }))

    expect(mockImportGuest).not.toHaveBeenCalled()
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeNull()
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeNull()
    expect(screen.queryByText(/continue your guest conversation/i)).not.toBeInTheDocument()
  })

  it('Continue imports and clears guest state', async () => {
    seedGuestConversation()
    armGuestContinuePrompt()
    mockImportGuest.mockResolvedValue({
      id: 'conv-imported',
      title: 'Guest conversation',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    const user = userEvent.setup()
    renderChat()

    await user.click(screen.getByRole('button', { name: /continue conversation/i }))

    await waitFor(() => {
      expect(mockImportGuest).toHaveBeenCalledTimes(1)
    })
    expect(mockImportGuest).toHaveBeenCalledWith({
      messages: [
        { role: 'user', content: 'What is RAG?' },
        { role: 'assistant', content: 'Retrieval-augmented generation.' },
      ],
      title: 'Guest conversation',
    })
    expect(mockAskQuestion).not.toHaveBeenCalled()
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeNull()
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeNull()
  })

  it('failed import preserves guest state', async () => {
    seedGuestConversation()
    armGuestContinuePrompt()
    mockImportGuest.mockRejectedValue(new Error('import failed'))
    const user = userEvent.setup()
    renderChat()

    await user.click(screen.getByRole('button', { name: /continue conversation/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeTruthy()
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeTruthy()
    expect(screen.getByText(/continue your guest conversation/i)).toBeInTheDocument()
    clearGuestImportPending()
  })
})
