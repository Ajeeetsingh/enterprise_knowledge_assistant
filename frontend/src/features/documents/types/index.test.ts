import { describe, expect, it } from 'vitest'

import {
  DocumentStatus,
  getDocumentDomainLabel,
  getStatusDisplay,
  getStatusLabel,
  UNCATEGORIZED_DOMAIN_LABEL,
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

describe('document domain label', () => {
  it('returns domain name when present', () => {
    expect(getDocumentDomainLabel({ domain_name: 'Finance' })).toBe('Finance')
  })

  it('returns Uncategorized for null or blank domain names', () => {
    expect(getDocumentDomainLabel({ domain_name: null })).toBe(UNCATEGORIZED_DOMAIN_LABEL)
    expect(getDocumentDomainLabel({ domain_name: '   ' })).toBe(UNCATEGORIZED_DOMAIN_LABEL)
  })
})
