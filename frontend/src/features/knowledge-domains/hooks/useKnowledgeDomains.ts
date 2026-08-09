import { useQuery } from '@tanstack/react-query'

import * as knowledgeDomainApi from '../services/knowledgeDomainApi'

export const knowledgeDomainQueryKeys = {
  all: ['knowledge-domains'] as const,
  list: () => [...knowledgeDomainQueryKeys.all, 'list'] as const,
}

export function useKnowledgeDomains() {
  return useQuery({
    queryKey: knowledgeDomainQueryKeys.list(),
    queryFn: () => knowledgeDomainApi.listKnowledgeDomains(),
  })
}
