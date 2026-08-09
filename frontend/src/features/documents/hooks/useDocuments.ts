import { useQuery } from '@tanstack/react-query'

import * as documentApi from '../services/documentApi'
import type { DocumentListParams } from '../types/listParams'
import { documentQueryKeys } from './queryKeys'

const DEFAULT_LIMIT = 50
const DEFAULT_OFFSET = 0

export function useDocuments(params: DocumentListParams = {}) {
  const {
    limit = DEFAULT_LIMIT,
    offset = DEFAULT_OFFSET,
    filename,
    status,
    domain_id,
  } = params

  return useQuery({
    queryKey: [
      ...documentQueryKeys.list(),
      { limit, offset, filename, status, domain_id },
    ],
    queryFn: () =>
      documentApi.getDocuments({
        limit,
        offset,
        ...(filename ? { filename } : {}),
        ...(status ? { status } : {}),
        ...(domain_id ? { domain_id } : {}),
      }),
  })
}

export function useDocument(documentId: string | null, enabled = true) {
  return useQuery({
    queryKey: documentQueryKeys.detail(documentId ?? ''),
    queryFn: () => documentApi.getDocument(documentId!),
    enabled: enabled && documentId !== null,
  })
}
