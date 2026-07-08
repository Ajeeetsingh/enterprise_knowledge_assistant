import { useCallback, useMemo, useState } from 'react'

import { SEED_COLLECTIONS } from '../data/seedCollections'
import type {
  AdminCollection,
  CreateCollectionInput,
  RenameCollectionInput,
} from '../types'
import { isCollectionNameTaken } from '../utils/collectionFilters'

function createLocalId(): string {
  return `col-${crypto.randomUUID()}`
}

function simulateNetworkDelay(ms = 250): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

export interface UseAdminCollectionsResult {
  collections: AdminCollection[]
  activeCollections: AdminCollection[]
  isCreating: boolean
  isUpdating: boolean
  isArchiving: boolean
  createCollection: (input: CreateCollectionInput) => Promise<AdminCollection>
  renameCollection: (id: string, input: RenameCollectionInput) => Promise<AdminCollection>
  archiveCollection: (id: string) => Promise<AdminCollection>
}

/**
 * Local-only collections state for Phase 10.5 (Path B).
 * Replace this hook with React Query + API client when backend collections ship.
 */
export function useAdminCollections(): UseAdminCollectionsResult {
  const [collections, setCollections] = useState<AdminCollection[]>(SEED_COLLECTIONS)
  const [isCreating, setIsCreating] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [isArchiving, setIsArchiving] = useState(false)

  const activeCollections = useMemo(
    () => collections.filter((collection) => !collection.is_archived),
    [collections],
  )

  const createCollection = useCallback(
    async (input: CreateCollectionInput): Promise<AdminCollection> => {
      setIsCreating(true)
      try {
        await simulateNetworkDelay()

        if (isCollectionNameTaken(collections, input.name)) {
          throw new Error('A collection with this name already exists.')
        }

        const now = new Date().toISOString()
        const created: AdminCollection = {
          id: createLocalId(),
          name: input.name.trim(),
          description: input.description?.trim() || null,
          document_count: 0,
          created_at: now,
          updated_at: now,
          is_archived: false,
        }

        setCollections((current) => [created, ...current])
        return created
      } finally {
        setIsCreating(false)
      }
    },
    [collections],
  )

  const renameCollection = useCallback(
    async (id: string, input: RenameCollectionInput): Promise<AdminCollection> => {
      setIsUpdating(true)
      try {
        await simulateNetworkDelay()

        if (isCollectionNameTaken(collections, input.name, id)) {
          throw new Error('A collection with this name already exists.')
        }

        let updatedCollection: AdminCollection | null = null

        setCollections((current) =>
          current.map((collection) => {
            if (collection.id !== id) return collection

            updatedCollection = {
              ...collection,
              name: input.name.trim(),
              updated_at: new Date().toISOString(),
            }
            return updatedCollection
          }),
        )

        if (!updatedCollection) {
          throw new Error('Collection not found.')
        }

        return updatedCollection
      } finally {
        setIsUpdating(false)
      }
    },
    [collections],
  )

  const archiveCollection = useCallback(async (id: string): Promise<AdminCollection> => {
    setIsArchiving(true)
    try {
      await simulateNetworkDelay()

      let archivedCollection: AdminCollection | null = null

      setCollections((current) =>
        current.map((collection) => {
          if (collection.id !== id) return collection

          archivedCollection = {
            ...collection,
            is_archived: true,
            updated_at: new Date().toISOString(),
          }
          return archivedCollection
        }),
      )

      if (!archivedCollection) {
        throw new Error('Collection not found.')
      }

      return archivedCollection
    } finally {
      setIsArchiving(false)
    }
  }, [])

  return {
    collections,
    activeCollections,
    isCreating,
    isUpdating,
    isArchiving,
    createCollection,
    renameCollection,
    archiveCollection,
  }
}
