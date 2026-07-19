import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { CreateUserRequest } from '../types'
import * as userApi from '../services/userApi'
import { userQueryKeys } from './queryKeys'

export type CreateUserInput = CreateUserRequest

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: CreateUserInput) => {
      return userApi.createUser(input)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userQueryKeys.list() })
    },
  })
}
