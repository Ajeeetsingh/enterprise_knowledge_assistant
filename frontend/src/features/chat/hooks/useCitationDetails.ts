import { useCallback, useEffect, useRef, useState } from 'react'

import {
  CitationDetailsError,
  resolveCitationDetails,
} from '../services/citationService'
import type { Citation, CitationDetails } from '../types'

export function useCitationDetails(citation: Citation | null) {
  const [details, setDetails] = useState<CitationDetails | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestIdRef = useRef(0)

  const load = useCallback(async (target: Citation) => {
    const requestId = ++requestIdRef.current
    setIsLoading(true)
    setError(null)

    try {
      const result = await resolveCitationDetails(target)
      if (requestId !== requestIdRef.current) return
      setDetails(result)
    } catch (loadError) {
      if (requestId !== requestIdRef.current) return
      setDetails(null)
      setError(
        loadError instanceof CitationDetailsError
          ? loadError.message
          : 'Unable to load citation details.',
      )
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    if (!citation) {
      requestIdRef.current += 1
      setDetails(null)
      setError(null)
      setIsLoading(false)
      return
    }

    void load(citation)
  }, [citation, load])

  const retry = useCallback(() => {
    if (citation) {
      void load(citation)
    }
  }, [citation, load])

  return { details, isLoading, error, retry }
}
