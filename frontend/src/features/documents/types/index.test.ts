import { describe, expect, it } from 'vitest'

import {
  DocumentStatus,
  getStatusDisplay,
  getStatusLabel,
} from '@/features/documents/types'

describe('document status display', () => {
  it('maps deleted status to DELETED display and label', () => {
    expect(getStatusDisplay(DocumentStatus.Deleted)).toBe('DELETED')
    expect(getStatusLabel(DocumentStatus.Deleted)).toBe('Deleted')
  })

  it('maps searchable status to READY display and label', () => {
    expect(getStatusDisplay(DocumentStatus.Searchable)).toBe('READY')
    expect(getStatusLabel(DocumentStatus.Searchable)).toBe('Ready')
  })

  it('maps processing status to PROCESSING display and label', () => {
    expect(getStatusDisplay(DocumentStatus.Processing)).toBe('PROCESSING')
    expect(getStatusLabel(DocumentStatus.Processing)).toBe('Processing')
  })
})
