import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

export async function fetchDocumentFileBlob(
  documentId: string,
  options: { download?: boolean } = {},
): Promise<Blob> {
  try {
    const { data } = await apiClient.get<Blob>(`/documents/${documentId}/file`, {
      responseType: 'blob',
      params: options.download ? { download: true } : undefined,
      timeout: 120_000,
    })
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export function createObjectUrlFromBlob(blob: Blob): string {
  return URL.createObjectURL(blob)
}

export function revokeObjectUrl(url: string): void {
  URL.revokeObjectURL(url)
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = createObjectUrlFromBlob(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  revokeObjectUrl(url)
}
