/**
 * Admin collection types — aligned with the planned backend contract.
 * Phase 10.5 uses local preview data until collection APIs exist.
 */

export interface AdminCollection {
  id: string
  name: string
  description: string | null
  document_count: number
  created_at: string
  updated_at: string
  is_archived: boolean
}

export interface CreateCollectionInput {
  name: string
  description?: string | null
}

export interface RenameCollectionInput {
  name: string
}

/** Future API integration surface (not implemented in Phase 10.5). */
export interface CollectionsDataSource {
  listCollections(): Promise<AdminCollection[]>
  createCollection(input: CreateCollectionInput): Promise<AdminCollection>
  renameCollection(id: string, input: RenameCollectionInput): Promise<AdminCollection>
  archiveCollection(id: string): Promise<AdminCollection>
}

export function formatCollectionDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
