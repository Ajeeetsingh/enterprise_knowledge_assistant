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
  } = params

  return useQuery({
    queryKey: [...documentQueryKeys.list(), { limit, offset, filename, status }],
    queryFn: () =>
      documentApi.getDocuments({
        limit,
        offset,
        ...(filename ? { filename } : {}),
        ...(status ? { status } : {}),
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
