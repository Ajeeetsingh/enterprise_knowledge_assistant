import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as userAnalyticsApi from '../services/userAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useTopUsers(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.topUsers(filters),
    queryFn: () => userAnalyticsApi.getTopUsers(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
