import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as aiAnalyticsApi from '../services/aiAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useAIAnalytics(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.aiOverview(filters),
    queryFn: () => aiAnalyticsApi.getAIAnalyticsOverview(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
