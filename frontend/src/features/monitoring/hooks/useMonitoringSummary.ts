import { useQuery } from '@tanstack/react-query'

import { MONITORING_REFRESH_INTERVAL_MS } from '../constants'
import * as monitoringApi from '../services/monitoringApi'
import { monitoringQueryKeys } from './queryKeys'

export function useMonitoringSummary() {
  return useQuery({
    queryKey: monitoringQueryKeys.summary(),
    queryFn: () => monitoringApi.getMonitoringSummary(),
    refetchInterval: MONITORING_REFRESH_INTERVAL_MS,
  })
}
