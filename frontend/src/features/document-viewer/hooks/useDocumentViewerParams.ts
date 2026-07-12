import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import type { DocumentViewerHighlightTarget, DocumentViewerParams } from '../types'

function parsePositiveInt(value: string | null): number | undefined {
  if (!value) return undefined
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined
}

export function parseDocumentViewerParams(
  searchParams: URLSearchParams,
): DocumentViewerParams {
  const params: DocumentViewerParams = {}
  const page = parsePositiveInt(searchParams.get('page'))
  if (page) params.page = page

  const chunkId = searchParams.get('chunkId')
  if (chunkId) params.chunkId = chunkId

  const highlightText = searchParams.get('highlightText')
  if (highlightText) params.highlightText = highlightText

  return params
}

export function useDocumentViewerParams(): DocumentViewerParams {
  const [searchParams] = useSearchParams()
  return useMemo(() => parseDocumentViewerParams(searchParams), [searchParams])
}

/** Maps URL params to a highlight target for future overlay renderers. */
export function useDocumentViewerHighlightTarget(): DocumentViewerHighlightTarget | null {
  const params = useDocumentViewerParams()
  if (params.page == null) {
    return null
  }

  const target: DocumentViewerHighlightTarget = { page: params.page }
  if (params.chunkId) target.chunkId = params.chunkId
  if (params.highlightText) target.highlightText = params.highlightText
  return target
}
