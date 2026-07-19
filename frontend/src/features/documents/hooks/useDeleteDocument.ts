import { useMutation, useQueryClient } from '@tanstack/react-query'

import { chatQueryKeys } from '@/features/chat/hooks/queryKeys'

import type { PaginatedDocumentResponse } from '../types'
import * as documentApi from '../services/documentApi'
import { documentQueryKeys } from './queryKeys'

export function useDeleteDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (documentId: string) => documentApi.deleteDocument(documentId),
    onSuccess: (_data, documentId) => {
      queryClient.setQueriesData<PaginatedDocumentResponse>(
        { queryKey: documentQueryKeys.list() },
        (current) => {
          if (!current) return current
          const items = current.items.filter((item) => item.document_id !== documentId)
          const removedCount = current.items.length - items.length
          return {
            ...current,
            items,
            total: Math.max(0, current.total - removedCount),
          }
        },
      )
      void queryClient.invalidateQueries({ queryKey: documentQueryKeys.list() })
      void queryClient.removeQueries({ queryKey: documentQueryKeys.detail(documentId) })
      // Removed content may change what questions are worth suggesting.
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.suggestedQuestions() })
    },
  })
}
