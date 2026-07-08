import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as userApi from '../services/userApi'
import type { User } from '../types'
import { userQueryKeys } from './queryKeys'

export interface UpdateUserRoleInput {
  userId: string
  user: User
  newRole: string
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, user, newRole }: UpdateUserRoleInput) => {
      for (const role of user.roles) {
        if (role !== newRole) {
          await userApi.removeUserRole(userId, role)
        }
      }

      if (!user.roles.includes(newRole)) {
        await userApi.assignUserRoles(userId, { roles: [newRole] })
      }
    },
    onSuccess: (_data, { userId }) => {
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.list() })
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.detail(userId) })
    },
  })
}
