import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as monitoringAnalyticsApi from '../services/monitoringAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function usePerformanceMetrics(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.monitoringPerformance(filters),
    queryFn: () => monitoringAnalyticsApi.getPerformanceMetrics(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
