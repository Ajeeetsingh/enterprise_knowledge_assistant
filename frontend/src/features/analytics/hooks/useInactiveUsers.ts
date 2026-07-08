import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as userAnalyticsApi from '../services/userAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useInactiveUsers(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.inactiveUsers(filters),
    queryFn: () => userAnalyticsApi.getInactiveUsers(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
