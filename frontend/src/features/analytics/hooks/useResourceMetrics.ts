import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as monitoringAnalyticsApi from '../services/monitoringAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useResourceMetrics(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.monitoringResources(filters),
    queryFn: () => monitoringAnalyticsApi.getResourceMetrics(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
