import { useQuery } from '@tanstack/react-query'

import { getReportFormats } from '../services/reportsApi'
import { reportsQueryKeys } from './queryKeys'

export function useReportFormats() {
  return useQuery({
    queryKey: reportsQueryKeys.formats(),
    queryFn: getReportFormats,
    staleTime: 60_000,
  })
}
