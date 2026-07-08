import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as knowledgeAnalyticsApi from '../services/knowledgeAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useDocumentAnalytics(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.knowledgeDocuments(filters),
    queryFn: () => knowledgeAnalyticsApi.getDocumentAnalytics(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
