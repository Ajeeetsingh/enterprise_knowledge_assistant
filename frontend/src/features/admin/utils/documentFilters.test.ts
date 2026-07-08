import { describe, expect, it } from 'vitest'

import { mockAdminDocuments } from '../test/documentFixtures'
import {
  applyDocumentFilters,
  filterDocumentsBySearch,
  filterDocumentsByStatus,
  filterDocumentsByVisibility,
} from './documentFilters'

describe('documentFilters', () => {
  it('filters documents by search term', () => {
    const result = filterDocumentsBySearch(mockAdminDocuments, 'employee')

    expect(result).toHaveLength(1)
    expect(result[0]?.filename).toBe('Employee Handbook.pdf')
  })

  it('filters documents by status group', () => {
    expect(filterDocumentsByStatus(mockAdminDocuments, 'READY')).toHaveLength(1)
    expect(filterDocumentsByStatus(mockAdminDocuments, 'PROCESSING')).toHaveLength(1)
    expect(filterDocumentsByStatus(mockAdminDocuments, 'FAILED')).toHaveLength(1)
  })

  it('filters documents by visibility', () => {
    expect(filterDocumentsByVisibility(mockAdminDocuments, 'PUBLIC')).toHaveLength(1)
    expect(filterDocumentsByVisibility(mockAdminDocuments, 'ROLE_BASED')).toHaveLength(1)
    expect(filterDocumentsByVisibility(mockAdminDocuments, 'PRIVATE')).toHaveLength(1)
  })

  it('applies combined filters', () => {
    const result = applyDocumentFilters(mockAdminDocuments, {
      status: 'READY',
      visibility: 'PUBLIC',
    })

    expect(result).toHaveLength(1)
    expect(result[0]?.filename).toBe('Employee Handbook.pdf')
  })
})
