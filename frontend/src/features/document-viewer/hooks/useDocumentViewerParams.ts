import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import type { DocumentViewerHighlightTarget, DocumentViewerParams } from '../types'
import { consumeCitationHighlight } from '../utils/citationHighlightStorage'

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

  const citeKey = searchParams.get('citeKey')
  if (citeKey) params.citeKey = citeKey

  const highlightText = searchParams.get('highlightText')
  if (highlightText) params.highlightText = highlightText

  return params
}

export function useDocumentViewerParams(): DocumentViewerParams {
  const [searchParams] = useSearchParams()
  return useMemo(() => parseDocumentViewerParams(searchParams), [searchParams])
}

/** Maps URL params (+ localStorage citeKey payload) to a highlight target. */
export function useDocumentViewerHighlightTarget(): DocumentViewerHighlightTarget | null {
  const params = useDocumentViewerParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [hydratedExcerpt, setHydratedExcerpt] = useState<string | undefined>(
    () => params.highlightText,
  )
  const consumedCiteKey = useRef<string | null>(null)

  useEffect(() => {
    if (params.citeKey && consumedCiteKey.current !== params.citeKey) {
      consumedCiteKey.current = params.citeKey
      const payload = consumeCitationHighlight(params.citeKey)
      if (payload?.excerpt) {
        setHydratedExcerpt(payload.excerpt)
      }

      if (searchParams.has('citeKey')) {
        const next = new URLSearchParams(searchParams)
        next.delete('citeKey')
        setSearchParams(next, { replace: true })
      }
      return
    }

    if (params.highlightText) {
      setHydratedExcerpt(params.highlightText)
    }
  }, [params.citeKey, params.highlightText, searchParams, setSearchParams])

  if (params.page == null) {
    return null
  }

  const target: DocumentViewerHighlightTarget = { page: params.page }
  if (params.chunkId) target.chunkId = params.chunkId
  if (hydratedExcerpt) target.highlightText = hydratedExcerpt
  return target
}
