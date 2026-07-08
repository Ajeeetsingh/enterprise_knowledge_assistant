import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as errorAnalyticsApi from '../services/errorAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useErrorTrends(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.errorsTrends(filters),
    queryFn: () => errorAnalyticsApi.getErrorTrends(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
