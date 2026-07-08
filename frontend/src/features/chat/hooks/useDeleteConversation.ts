import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import { chatQueryKeys } from './queryKeys'

export function useDeleteConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (conversationId: string) => chatApi.deleteConversation(conversationId),
    onSuccess: (_data, conversationId) => {
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations() })
      void queryClient.removeQueries({ queryKey: chatQueryKeys.messages(conversationId) })
    },
  })
}
