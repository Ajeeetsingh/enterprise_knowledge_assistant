import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as documentApi from '../services/documentApi'
import { documentQueryKeys } from './queryKeys'

export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => documentApi.uploadDocument(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: documentQueryKeys.list() })
    },
  })
}
