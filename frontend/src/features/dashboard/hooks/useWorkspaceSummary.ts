import { useQuery } from '@tanstack/react-query'

import * as workspaceApi from '../services/workspaceApi'
import { dashboardQueryKeys } from './queryKeys'

export function useWorkspaceSummary() {
  return useQuery({
    queryKey: dashboardQueryKeys.summary(),
    queryFn: () => workspaceApi.getWorkspaceSummary(),
  })
}
