import type { DocumentViewerParams } from '../types'

export function buildDocumentViewerUrl(
  documentId: string,
  params: DocumentViewerParams = {},
): string {
  const search = new URLSearchParams()

  if (params.page != null && params.page > 0) {
    search.set('page', String(params.page))
  }
  if (params.chunkId) {
    search.set('chunkId', params.chunkId)
  }
  if (params.highlightText) {
    search.set('highlightText', params.highlightText)
  }

  const query = search.toString()
  return `/documents/${documentId}${query ? `?${query}` : ''}`
}
