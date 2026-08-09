import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { Document, PaginatedDocumentResponse } from '../types'
import * as documentApi from '../services/documentApi'
import { documentQueryKeys } from './queryKeys'

export interface UpdateDocumentDomainVariables {
  documentId: string
  domainId: string | null
}

export function useUpdateDocumentDomain() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ documentId, domainId }: UpdateDocumentDomainVariables) =>
      documentApi.updateDocumentDomain(documentId, domainId),
    onSuccess: (updated: Document) => {
      queryClient.setQueriesData<PaginatedDocumentResponse>(
        { queryKey: documentQueryKeys.list() },
        (current) => {
          if (!current) return current
          return {
            ...current,
            items: current.items.map((item) =>
              item.document_id === updated.document_id
                ? {
                    ...item,
                    domain_id: updated.domain_id ?? null,
                    domain_name: updated.domain_name ?? null,
                  }
                : item,
            ),
          }
        },
      )
      void queryClient.invalidateQueries({ queryKey: documentQueryKeys.list() })
      void queryClient.invalidateQueries({
        queryKey: documentQueryKeys.detail(updated.document_id),
      })
    },
  })
}
