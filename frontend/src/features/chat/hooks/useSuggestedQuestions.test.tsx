import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { SuggestedQuestionsResponse } from '@/features/chat/types'

const getSuggestedQuestions = vi.fn<() => Promise<SuggestedQuestionsResponse>>()

vi.mock('@/features/chat/services/chatApi', () => ({
  getSuggestedQuestions: () => getSuggestedQuestions(),
}))

import { useSuggestedQuestions } from '@/features/chat/hooks/useSuggestedQuestions'

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useSuggestedQuestions', () => {
  it('fetches and returns contextual suggested questions', async () => {
    const response: SuggestedQuestionsResponse = {
      items: [
        { text: 'What are the main commercial paper issuers?', source: 'commercial_paper.pdf' },
        { text: 'Explain the repo market.', source: 'treasury_repo.pdf' },
      ],
    }
    getSuggestedQuestions.mockResolvedValueOnce(response)
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    const { result } = renderHook(() => useSuggestedQuestions(), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(response)
    expect(getSuggestedQuestions).toHaveBeenCalledTimes(1)
  })

  it('surfaces an error state when the request fails', async () => {
    getSuggestedQuestions.mockRejectedValueOnce(new Error('network error'))
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    const { result } = renderHook(() => useSuggestedQuestions(), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
