import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as aiAnalyticsApi from '../services/aiAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useAITrends(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.aiTrends(filters),
    queryFn: () => aiAnalyticsApi.getAITrends(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
