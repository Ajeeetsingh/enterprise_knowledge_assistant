import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import type { ChatRequest } from '../types'
import { chatQueryKeys } from './queryKeys'

export function useAskQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ChatRequest) => chatApi.askQuestion(body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: chatQueryKeys.messages(variables.conversation_id),
      })
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations() })
    },
  })
}
