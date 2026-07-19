import { describe, expect, it } from 'vitest'

import { buildDocumentViewerUrl } from './buildViewerUrl'
import { parseDocumentViewerParams } from '../hooks/useDocumentViewerParams'

describe('buildDocumentViewerUrl', () => {
  it('builds a document viewer path without query params', () => {
    expect(buildDocumentViewerUrl('doc-123')).toBe('/documents/doc-123')
  })

  it('includes page, chunkId, citeKey, and highlightText query params', () => {
    expect(
      buildDocumentViewerUrl('doc-123', {
        page: 13,
        chunkId: 'chunk-9',
        citeKey: 'cite-abc',
        highlightText: 'revenue',
      }),
    ).toBe(
      '/documents/doc-123?page=13&chunkId=chunk-9&citeKey=cite-abc&highlightText=revenue',
    )
  })
})

describe('parseDocumentViewerParams', () => {
  it('parses citation navigation params including citeKey', () => {
    const params = parseDocumentViewerParams(
      new URLSearchParams('page=5&citeKey=ck-1&chunkId=c-9'),
    )
    expect(params).toEqual({
      page: 5,
      citeKey: 'ck-1',
      chunkId: 'c-9',
    })
  })

  it('ignores invalid page values', () => {
    expect(parseDocumentViewerParams(new URLSearchParams('page=0')).page).toBeUndefined()
    expect(parseDocumentViewerParams(new URLSearchParams('page=-2')).page).toBeUndefined()
  })
})
