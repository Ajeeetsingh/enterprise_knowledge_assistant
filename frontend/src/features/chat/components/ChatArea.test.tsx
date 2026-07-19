import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '@/contexts/ToastContext'

import type { SuggestedQuestionsResponse } from '../types'
import ChatArea from './ChatArea'

const mockMutateAsync = vi.fn()
const mockUseSuggestedQuestions = vi.fn()

vi.mock('./ChatHeader', () => ({
  default: () => null,
}))

vi.mock('./MessageList', () => ({
  default: () => null,
}))

vi.mock('../hooks/useConversationMessages', () => ({
  useConversationMessages: () => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
  }),
}))

vi.mock('../hooks/useAskQuestion', () => ({
  useAskQuestion: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}))

vi.mock('../hooks/useSuggestedQuestions', () => ({
  useSuggestedQuestions: () => mockUseSuggestedQuestions(),
}))

function renderChatArea() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ChatArea conversationId="conv-1" />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('ChatArea empty state suggestions', () => {
  it('shows a loading skeleton while suggestions are being fetched', async () => {
    mockUseSuggestedQuestions.mockReturnValue({ data: undefined, isLoading: true })

    renderChatArea()

    expect(await screen.findByText('Suggested questions')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /issuers/i })).not.toBeInTheDocument()
  })

  it('renders dynamic suggested questions once loaded', async () => {
    const response: SuggestedQuestionsResponse = {
      items: [
        { text: 'What are the main commercial paper issuers?', source: 'commercial_paper.pdf' },
        { text: 'Explain the repo market.', source: 'treasury_repo.pdf' },
      ],
    }
    mockUseSuggestedQuestions.mockReturnValue({ data: response, isLoading: false })

    renderChatArea()

    expect(
      await screen.findByRole('button', { name: 'What are the main commercial paper issuers?' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Explain the repo market.' })).toBeInTheDocument()
  })

  it('falls back to generic onboarding prompts when no suggestions are returned', async () => {
    mockUseSuggestedQuestions.mockReturnValue({ data: { items: [] }, isLoading: false })

    renderChatArea()

    expect(
      await screen.findByRole('button', { name: 'What can this assistant help me with?' }),
    ).toBeInTheDocument()
  })

  it('sends the question immediately when a suggestion is clicked', async () => {
    const response: SuggestedQuestionsResponse = {
      items: [{ text: 'What are the main commercial paper issuers?', source: 'commercial_paper.pdf' }],
    }
    mockUseSuggestedQuestions.mockReturnValue({ data: response, isLoading: false })
    mockMutateAsync.mockResolvedValueOnce({
      answer: 'Large corporations and financial institutions.',
      citations: [],
      confidence_score: 0.9,
    })
    const user = userEvent.setup()

    renderChatArea()
    const button = await screen.findByRole('button', {
      name: 'What are the main commercial paper issuers?',
    })
    await user.click(button)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        conversation_id: 'conv-1',
        question: 'What are the main commercial paper issuers?',
      })
    })
  })
})
