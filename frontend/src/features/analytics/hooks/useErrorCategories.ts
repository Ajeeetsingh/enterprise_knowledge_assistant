import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as errorAnalyticsApi from '../services/errorAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useErrorCategories(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.errorsCategories(filters),
    queryFn: () => errorAnalyticsApi.getErrorCategories(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
