import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as userApi from '../services/userApi'
import type { User } from '../types'
import { userQueryKeys } from './queryKeys'

export interface ToggleUserStatusInput {
  user: User
  enable: boolean
}

export function useToggleUserStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ user, enable }: ToggleUserStatusInput) => {
      if (enable) {
        return userApi.updateUser(user.id, {
          full_name: user.full_name,
          email: user.email,
          is_active: true,
        })
      }

      return userApi.disableUser(user.id)
    },
    onSuccess: (updatedUser) => {
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.list() })
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.detail(updatedUser.id) })
    },
  })
}
