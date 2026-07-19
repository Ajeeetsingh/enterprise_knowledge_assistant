import { describe, expect, it } from 'vitest'

import type { BatchUploadItem } from '../hooks/useUploadDocuments'
import type { Document } from '../types'
import { resolveHighlightDocumentId } from './duplicateHighlight'

function doc(id: string, filename = `${id}.pdf`): Document {
  return {
    document_id: id,
    filename,
    status: 'searchable',
    uploaded_at: '2026-01-01T00:00:00Z',
    uploaded_by: 'user-1',
  }
}

function item(
  partial: Pick<BatchUploadItem, 'status'> &
    Partial<BatchUploadItem> & { filename?: string },
): BatchUploadItem {
  const file = new File(['x'], partial.filename ?? 'file.pdf', { type: 'application/pdf' })
  return {
    id: partial.id ?? file.name,
    file,
    filename: partial.filename ?? file.name,
    size: file.size,
    status: partial.status,
    error: partial.error,
    existingDocumentId: partial.existingDocumentId,
  }
}

describe('resolveHighlightDocumentId', () => {
  it('returns the first visible authorized duplicate id', () => {
    const result = resolveHighlightDocumentId(
      [
        item({
          status: 'duplicate',
          filename: 'a.pdf',
          existingDocumentId: 'doc-a',
        }),
        item({
          status: 'duplicate',
          filename: 'b.pdf',
          existingDocumentId: 'doc-b',
        }),
      ],
      [doc('doc-a'), doc('doc-b')],
    )

    expect(result).toBe('doc-a')
  })

  it('skips duplicates that are not rendered in the current list', () => {
    const result = resolveHighlightDocumentId(
      [
        item({
          status: 'duplicate',
          filename: 'hidden.pdf',
          existingDocumentId: 'not-visible',
        }),
        item({
          status: 'duplicate',
          filename: 'visible.pdf',
          existingDocumentId: 'visible',
        }),
      ],
      [doc('visible')],
    )

    expect(result).toBe('visible')
  })

  it('returns null when no duplicate has an authorized document id', () => {
    const result = resolveHighlightDocumentId(
      [
        item({ status: 'duplicate', filename: 'a.pdf' }),
        item({ status: 'failed', filename: 'b.pdf', error: 'boom' }),
      ],
      [doc('doc-a')],
    )

    expect(result).toBeNull()
  })

  it('returns null when matching documents are off the current page', () => {
    const result = resolveHighlightDocumentId(
      [
        item({
          status: 'duplicate',
          filename: 'a.pdf',
          existingDocumentId: 'page-2-doc',
        }),
      ],
      [doc('page-1-doc')],
    )

    expect(result).toBeNull()
  })
})
