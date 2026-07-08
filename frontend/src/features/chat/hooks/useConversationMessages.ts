import { useQuery } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import { normalizeMessageCitations, type Message } from '../types'
import { chatQueryKeys } from './queryKeys'

function mapMessages(response: Awaited<ReturnType<typeof chatApi.getMessages>>): Message[] {
  return response.items.map((item) => ({
    ...item,
    role: item.role as Message['role'],
    citations: normalizeMessageCitations(item.citations),
  }))
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: chatQueryKeys.messages(conversationId ?? ''),
    queryFn: async () => {
      if (!conversationId) return []
      const response = await chatApi.getMessages(conversationId)
      return mapMessages(response)
    },
    enabled: Boolean(conversationId),
  })
}
