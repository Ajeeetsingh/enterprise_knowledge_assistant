import { useCallback, useEffect, useState } from 'react'

import type { PdfSearchMatch } from '../types'

export interface SearchablePdfDocument {
  numPages: number
  getPage: (pageNumber: number) => Promise<{
    getTextContent: () => Promise<{ items: Array<{ str?: string }> }>
  }>
}

async function findMatchesInDocument(
  pdf: SearchablePdfDocument,
  query: string,
): Promise<PdfSearchMatch[]> {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    return []
  }

  const matches: PdfSearchMatch[] = []
  let matchIndex = 0

  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber)
    const textContent = await page.getTextContent()
    const pageText = textContent.items
      .map((item) => item.str ?? '')
      .join(' ')
      .toLowerCase()

    let startAt = 0
    while (true) {
      const foundAt = pageText.indexOf(normalized, startAt)
      if (foundAt === -1) break
      matches.push({ pageNumber, matchIndex })
      matchIndex += 1
      startAt = foundAt + normalized.length
    }
  }

  return matches
}

export function usePdfTextSearch(pdf: SearchablePdfDocument | null, query: string) {
  const [matches, setMatches] = useState<PdfSearchMatch[]>([])
  const [activeMatchIndex, setActiveMatchIndex] = useState(0)
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    if (!pdf || !query.trim()) {
      setMatches([])
      setActiveMatchIndex(0)
      return
    }

    let cancelled = false
    setIsSearching(true)

    void findMatchesInDocument(pdf, query)
      .then((found) => {
        if (cancelled) return
        setMatches(found)
        setActiveMatchIndex(0)
      })
      .finally(() => {
        if (!cancelled) setIsSearching(false)
      })

    return () => {
      cancelled = true
    }
  }, [pdf, query])

  const goToNextMatch = useCallback(() => {
    if (matches.length === 0) return null
    const next = (activeMatchIndex + 1) % matches.length
    setActiveMatchIndex(next)
    return matches[next] ?? null
  }, [activeMatchIndex, matches])

  const goToPreviousMatch = useCallback(() => {
    if (matches.length === 0) return null
    const prev = (activeMatchIndex - 1 + matches.length) % matches.length
    setActiveMatchIndex(prev)
    return matches[prev] ?? null
  }, [activeMatchIndex, matches])

  const activeMatch = matches[activeMatchIndex] ?? null

  return {
    matches,
    activeMatch,
    activeMatchIndex,
    isSearching,
    goToNextMatch,
    goToPreviousMatch,
  }
}
