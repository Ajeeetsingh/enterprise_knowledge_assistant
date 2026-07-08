import { useQuery } from '@tanstack/react-query'

import { ANALYTICS_REFRESH_INTERVAL_MS } from '../constants'
import * as monitoringAnalyticsApi from '../services/monitoringAnalyticsApi'
import type { AnalyticsFilterParams } from '../types'
import { analyticsQueryKeys } from './queryKeys'

export function useHealthTimeline(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.monitoringTrends(filters),
    queryFn: () => monitoringAnalyticsApi.getMonitoringTrends(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
    select: (data) => ({
      items: data.timeline_items,
      total: data.timeline_total,
      limit: data.timeline_limit,
      offset: data.timeline_offset,
      start_date: data.start_date,
      end_date: data.end_date,
    }),
  })
}

export function useMonitoringTrends(filters: AnalyticsFilterParams = {}) {
  return useQuery({
    queryKey: analyticsQueryKeys.monitoringTrends(filters),
    queryFn: () => monitoringAnalyticsApi.getMonitoringTrends(filters),
    refetchInterval: ANALYTICS_REFRESH_INTERVAL_MS,
  })
}
