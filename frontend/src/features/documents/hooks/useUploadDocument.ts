import { useMutation, useQueryClient } from '@tanstack/react-query'

import * as documentApi from '../services/documentApi'
import { logUploadTransition } from '../utils/uploadLifecycleDebug'
import { documentQueryKeys } from './queryKeys'

export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => documentApi.uploadDocument(file),
    onMutate: (file) => {
      logUploadTransition('useUploadDocument', 'Uploading', {
        filename: file.name,
        sizeBytes: file.size,
      })
    },
    onSuccess: (response, file) => {
      logUploadTransition('useUploadDocument', 'Uploaded', {
        filename: file.name,
        documentId: response.document_id,
        backendStatus: response.status,
      })
      void queryClient.invalidateQueries({ queryKey: documentQueryKeys.list() })
    },
    onError: (error, file) => {
      logUploadTransition('useUploadDocument', 'Failed', {
        filename: file.name,
        error: error instanceof Error ? error.message : String(error),
      })
    },
  })
}
