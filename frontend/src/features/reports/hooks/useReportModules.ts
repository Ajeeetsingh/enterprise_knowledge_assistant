import { useQuery } from '@tanstack/react-query'

import { getReportModules } from '../services/reportsApi'
import { reportsQueryKeys } from './queryKeys'

export function useReportModules() {
  return useQuery({
    queryKey: reportsQueryKeys.modules(),
    queryFn: getReportModules,
    staleTime: 60_000,
  })
}
