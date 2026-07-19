import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  CITATION_HIGHLIGHT_STORAGE_PREFIX,
  consumeCitationHighlight,
  storeCitationHighlight,
} from './citationHighlightStorage'

afterEach(() => {
  localStorage.clear()
})

describe('citationHighlightStorage', () => {
  it('stores and consumes a citation excerpt once', () => {
    const key = storeCitationHighlight({
      excerpt: 'Employees are entitled to 20 days of annual leave.',
      page: 14,
    })
    expect(key).toBeTruthy()
    expect(localStorage.getItem(`${CITATION_HIGHLIGHT_STORAGE_PREFIX}${key}`)).toBeTruthy()

    const payload = consumeCitationHighlight(key!)
    expect(payload).toEqual({
      excerpt: 'Employees are entitled to 20 days of annual leave.',
      page: 14,
      storedAt: expect.any(Number),
    })
    expect(consumeCitationHighlight(key!)).toBeNull()
  })

  it('rejects empty excerpts', () => {
    expect(storeCitationHighlight({ excerpt: '   ' })).toBeNull()
  })

  it('returns null for unknown keys', () => {
    expect(consumeCitationHighlight('missing-key')).toBeNull()
  })
})
