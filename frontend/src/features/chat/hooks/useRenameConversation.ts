import { useMutation, useQueryClient } from '@tanstack/react-query'

import { CONVERSATION_RENAME_API_AVAILABLE, RENAME_UNAVAILABLE_MESSAGE } from '../constants'
import * as chatApi from '../services/chatApi'
import { chatQueryKeys } from './queryKeys'

interface RenameConversationInput {
  conversationId: string
  title: string
}

export function useRenameConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ conversationId, title }: RenameConversationInput) => {
      if (!CONVERSATION_RENAME_API_AVAILABLE) {
        throw { message: RENAME_UNAVAILABLE_MESSAGE, status: 501 }
      }
      return chatApi.updateConversation(conversationId, { title })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations() })
    },
  })
}
