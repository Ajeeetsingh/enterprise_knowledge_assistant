import type { AdminCollection } from '../types'

export function filterCollectionsByName(
  collections: AdminCollection[],
  search: string,
): AdminCollection[] {
  const query = search.trim().toLowerCase()
  if (!query) return collections

  return collections.filter((collection) => collection.name.toLowerCase().includes(query))
}

export function getActiveCollections(collections: AdminCollection[]): AdminCollection[] {
  return collections.filter((collection) => !collection.is_archived)
}

export function isCollectionNameTaken(
  collections: AdminCollection[],
  name: string,
  excludeId?: string,
): boolean {
  const normalized = name.trim().toLowerCase()
  return collections.some(
    (collection) =>
      collection.id !== excludeId && collection.name.trim().toLowerCase() === normalized,
  )
}

export function validateCollectionName(name: string): string | null {
  const trimmed = name.trim()
  if (!trimmed) return 'Collection name is required.'
  if (trimmed.length > 120) return 'Collection name must be 120 characters or fewer.'
  return null
}
