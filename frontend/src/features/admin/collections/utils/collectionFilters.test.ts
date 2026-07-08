import { describe, expect, it } from 'vitest'

import { SEED_COLLECTIONS } from '../data/seedCollections'
import {
  filterCollectionsByName,
  isCollectionNameTaken,
  validateCollectionName,
} from './collectionFilters'

describe('collectionFilters', () => {
  it('filters collections by name', () => {
    expect(filterCollectionsByName(SEED_COLLECTIONS, 'finance')).toHaveLength(1)
    expect(filterCollectionsByName(SEED_COLLECTIONS, 'hr')).toHaveLength(1)
  })

  it('validates collection names', () => {
    expect(validateCollectionName('')).toBe('Collection name is required.')
    expect(validateCollectionName('Finance')).toBeNull()
  })

  it('detects duplicate collection names', () => {
    expect(isCollectionNameTaken(SEED_COLLECTIONS, 'Finance')).toBe(true)
    expect(isCollectionNameTaken(SEED_COLLECTIONS, 'Legal')).toBe(false)
  })
})
