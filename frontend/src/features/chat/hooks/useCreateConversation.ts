import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import { chatQueryKeys } from './queryKeys'

export function useCreateConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => chatApi.createConversation({ title: null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversations() })
    },
  })
}
