/**
 * Short-lived bridge for citation highlight context across a newly opened tab.
 * Uses localStorage (not sessionStorage) so the chat tab can hand off excerpt
 * text to a target=_blank viewer tab without putting content in the URL.
 */

export const CITATION_HIGHLIGHT_STORAGE_PREFIX = 'eka:citation-highlight:'

/** Discard payloads older than this (ms). */
const MAX_AGE_MS = 60 * 60 * 1000

export interface CitationHighlightPayload {
  excerpt: string
  page?: number
  storedAt: number
}

function storageKey(citeKey: string): string {
  return `${CITATION_HIGHLIGHT_STORAGE_PREFIX}${citeKey}`
}

function createCiteKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `cite-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * Persist citation excerpt for the document viewer tab.
 * Returns a short opaque key suitable for a URL query param.
 */
export function storeCitationHighlight(input: {
  excerpt: string
  page?: number
}): string | null {
  const excerpt = input.excerpt.trim()
  if (!excerpt) return null

  const citeKey = createCiteKey()
  const payload: CitationHighlightPayload = {
    excerpt,
    storedAt: Date.now(),
  }
  if (typeof input.page === 'number' && input.page > 0) {
    payload.page = input.page
  }

  try {
    localStorage.setItem(storageKey(citeKey), JSON.stringify(payload))
  } catch {
    return null
  }
  return citeKey
}

/**
 * Read and remove a stored highlight payload (one-shot).
 */
export function consumeCitationHighlight(citeKey: string): CitationHighlightPayload | null {
  if (!citeKey.trim()) return null

  let raw: string | null
  try {
    raw = localStorage.getItem(storageKey(citeKey))
  } catch {
    return null
  }
  if (!raw) return null

  try {
    localStorage.removeItem(storageKey(citeKey))
  } catch {
    // ignore removal failures
  }

  try {
    const parsed = JSON.parse(raw) as Partial<CitationHighlightPayload>
    if (typeof parsed.excerpt !== 'string' || !parsed.excerpt.trim()) {
      return null
    }
    const storedAt = typeof parsed.storedAt === 'number' ? parsed.storedAt : 0
    if (storedAt > 0 && Date.now() - storedAt > MAX_AGE_MS) {
      return null
    }
    const payload: CitationHighlightPayload = {
      excerpt: parsed.excerpt,
      storedAt,
    }
    if (typeof parsed.page === 'number' && parsed.page > 0) {
      payload.page = parsed.page
    }
    return payload
  } catch {
    return null
  }
}
