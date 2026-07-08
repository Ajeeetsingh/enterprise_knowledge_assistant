/**
 * Citation detail resolution (Phase 10.0.2).
 *
 * No dedicated backend citation endpoint exists yet — details are resolved
 * from citation objects already returned with chat/message responses.
 */

import type { Citation, CitationDetails } from '../types'

export class CitationDetailsError extends Error {
  constructor(message = 'Unable to load citation details.') {
    super(message)
    this.name = 'CitationDetailsError'
  }
}

export async function resolveCitationDetails(citation: Citation): Promise<CitationDetails> {
  if (!citation.source?.trim()) {
    throw new CitationDetailsError()
  }

  return {
    source: citation.source.trim(),
    excerpt: citation.excerpt?.trim() ? citation.excerpt.trim() : null,
    confidence: citation.confidence,
    page: typeof citation.page === 'number' ? citation.page : null,
    ...(citation.metadata ? { metadata: citation.metadata } : {}),
  }
}
