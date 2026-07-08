import { useQuery } from '@tanstack/react-query'

import { MONITORING_REFRESH_INTERVAL_MS } from '../constants'
import * as monitoringApi from '../services/monitoringApi'
import { monitoringQueryKeys } from './queryKeys'

export function useSystemMetrics() {
  return useQuery({
    queryKey: monitoringQueryKeys.metrics(),
    queryFn: () => monitoringApi.getSystemMetrics(),
    refetchInterval: MONITORING_REFRESH_INTERVAL_MS,
  })
}
