import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import {
  createObjectUrlFromBlob,
  fetchDocumentFileBlob,
  revokeObjectUrl,
} from '../services/documentFileApi'

export function useDocumentFileSource(documentId: string | undefined) {
  const query = useQuery({
    queryKey: ['documents', 'file', documentId],
    queryFn: () => fetchDocumentFileBlob(documentId!),
    enabled: Boolean(documentId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!query.data) {
      setObjectUrl(null)
      return
    }

    const url = createObjectUrlFromBlob(query.data)
    setObjectUrl(url)
    return () => revokeObjectUrl(url)
  }, [query.data])

  return {
    blob: query.data,
    fileUrl: objectUrl,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}
