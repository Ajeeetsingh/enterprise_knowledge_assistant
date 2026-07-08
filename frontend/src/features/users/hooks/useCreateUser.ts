import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { CreateUserRequest } from '../types'
import * as userApi from '../services/userApi'
import { userQueryKeys } from './queryKeys'

export interface CreateUserInput extends CreateUserRequest {
  role: string
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: CreateUserInput) => {
      const { role, ...body } = input
      const user = await userApi.createUser(body)
      await userApi.assignUserRoles(user.id, { roles: [role] })
      return user
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.list() })
    },
  })
}
