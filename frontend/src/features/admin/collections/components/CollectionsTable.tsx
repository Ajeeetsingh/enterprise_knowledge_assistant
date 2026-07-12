import ActionButton from '@/components/ui/ActionButton'
import EmptyState from '@/components/ui/EmptyState'

import { formatCollectionDate, type AdminCollection } from '../types'

export interface CollectionsTableProps {
  collections: AdminCollection[]
  isLoading?: boolean
  onView: (collection: AdminCollection) => void
  onRename: (collection: AdminCollection) => void
  onArchive: (collection: AdminCollection) => void
}

export default function CollectionsTable({
  collections,
  isLoading = false,
  onView,
  onRename,
  onArchive,
}: CollectionsTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading collections">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-overlay"
          />
        ))}
      </div>
    )
  }

  if (collections.length === 0) {
    return (
      <EmptyState
        title="No collections found"
        description="Create a collection to organize enterprise knowledge by department or topic."
      />
    )
  }

  return (
    <div className="data-table-shell">
      <table className="data-table">
        <caption className="sr-only">Knowledge collections</caption>
        <thead>
          <tr>
            <th scope="col">Collection</th>
            <th scope="col">Documents</th>
            <th scope="col">Created</th>
            <th scope="col" className="text-right">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {collections.map((collection) => (
            <tr key={collection.id} className="interactive-row">
              <td className="font-medium">{collection.name}</td>
              <td className="text-muted">{collection.document_count}</td>
              <td className="text-muted">{formatCollectionDate(collection.created_at)}</td>
              <td>
                <div className="flex justify-end gap-2">
                  <ActionButton onClick={() => onView(collection)}>View</ActionButton>
                  <ActionButton onClick={() => onRename(collection)}>Rename</ActionButton>
                  <ActionButton destructive onClick={() => onArchive(collection)}>
                    Archive
                  </ActionButton>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
