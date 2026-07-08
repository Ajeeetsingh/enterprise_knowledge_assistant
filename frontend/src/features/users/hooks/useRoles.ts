import { useQuery } from '@tanstack/react-query'

import * as userApi from '../services/userApi'
import { userQueryKeys } from './queryKeys'

export function useRoles() {
  return useQuery({
    queryKey: userQueryKeys.roles(),
    queryFn: () => userApi.getRoles(),
  })
}
