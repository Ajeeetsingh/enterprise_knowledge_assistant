import { useQuery } from '@tanstack/react-query'

import * as userApi from '../services/userApi'
import { userQueryKeys } from './queryKeys'

export function useUsers() {
  return useQuery({
    queryKey: userQueryKeys.list(),
    queryFn: () => userApi.getUsers(),
  })
}

export function useUser(userId: string | null, enabled = true) {
  return useQuery({
    queryKey: userQueryKeys.detail(userId ?? ''),
    queryFn: () => userApi.getUser(userId!),
    enabled: enabled && userId !== null,
  })
}
