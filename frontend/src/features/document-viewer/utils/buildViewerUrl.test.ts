import { describe, expect, it } from 'vitest'

import { buildDocumentViewerUrl } from './buildViewerUrl'

describe('buildDocumentViewerUrl', () => {
  it('builds a document viewer path without query params', () => {
    expect(buildDocumentViewerUrl('doc-123')).toBe('/documents/doc-123')
  })

  it('includes page, chunkId, and highlightText query params', () => {
    expect(
      buildDocumentViewerUrl('doc-123', {
        page: 13,
        chunkId: 'chunk-9',
        highlightText: 'revenue',
      }),
    ).toBe('/documents/doc-123?page=13&chunkId=chunk-9&highlightText=revenue')
  })
})
