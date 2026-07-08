import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as userApi from '../services/userApi'
import { userQueryKeys } from './queryKeys'

export function useDisableUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: string) => userApi.disableUser(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.list() })
    },
  })
}
