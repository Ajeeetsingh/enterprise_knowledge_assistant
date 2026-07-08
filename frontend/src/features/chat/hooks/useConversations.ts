import { useQuery } from '@tanstack/react-query'

import * as chatApi from '../services/chatApi'
import { chatQueryKeys } from './queryKeys'

export function useConversations() {
  return useQuery({
    queryKey: chatQueryKeys.conversations(),
    queryFn: () => chatApi.getConversations(),
  })
}
