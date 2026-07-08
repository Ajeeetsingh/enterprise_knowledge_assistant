import { useQuery } from '@tanstack/react-query'

import * as documentApi from '@/features/documents/services/documentApi'
import { documentQueryKeys } from '@/features/documents/hooks/queryKeys'

import { RECENT_UPLOADS_LIMIT, RECENT_UPLOADS_POLL_INTERVAL_MS } from '../constants/uploads'
import { shouldPollRecentUploads } from '../utils/uploadStatus'

export function useRecentUploads() {
  return useQuery({
    queryKey: [...documentQueryKeys.list(), 'recent', RECENT_UPLOADS_LIMIT],
    queryFn: () => documentApi.getDocuments({ limit: RECENT_UPLOADS_LIMIT, offset: 0 }),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      if (!shouldPollRecentUploads(items)) return false
      return RECENT_UPLOADS_POLL_INTERVAL_MS
    },
  })
}
