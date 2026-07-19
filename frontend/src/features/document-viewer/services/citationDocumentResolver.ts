import { getDocuments } from '@/features/documents/services/documentApi'
import type { Citation } from '@/features/chat/types'

import type { DocumentViewerParams } from '../types'

export function getCitationDocumentId(citation: Citation): string | null {
  const raw = citation.metadata?.document_id
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return null
}

export function getCitationChunkId(citation: Citation): string | undefined {
  const raw = citation.metadata?.chunk_id
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return undefined
}

export function buildCitationViewerParams(citation: Citation): DocumentViewerParams {
  const params: DocumentViewerParams = {}
  if (typeof citation.page === 'number' && citation.page > 0) {
    params.page = citation.page
  }
  const chunkId = getCitationChunkId(citation)
  if (chunkId) {
    params.chunkId = chunkId
  }
  // Excerpt is passed via localStorage (citeKey), never as raw URL text.
  return params
}

export async function resolveCitationDocumentId(citation: Citation): Promise<string | null> {
  const fromMetadata = getCitationDocumentId(citation)
  if (fromMetadata) {
    return fromMetadata
  }

  const { items } = await getDocuments({ filename: citation.source, limit: 25 })
  const exact = items.find((document) => document.filename === citation.source)
  if (exact) {
    return exact.document_id
  }

  return items[0]?.document_id ?? null
}
