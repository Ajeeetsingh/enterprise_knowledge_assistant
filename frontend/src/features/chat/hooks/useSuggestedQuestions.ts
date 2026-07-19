import { useQuery } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import { chatQueryKeys } from './queryKeys'

/**
 * Contextual, AI-generated suggested questions for the chat empty state.
 *
 * The backend caches the expensive part (heading mining / LLM generation)
 * and only regenerates it when documents are uploaded, deleted, or
 * reindexed — so a long `staleTime` here just avoids redundant refetches on
 * remount within the same session; it does not affect correctness.
 */
export function useSuggestedQuestions() {
  return useQuery({
    queryKey: chatQueryKeys.suggestedQuestions(),
    queryFn: () => chatApi.getSuggestedQuestions(),
    staleTime: 5 * 60 * 1000,
  })
}
