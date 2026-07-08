import Button from '@/components/ui/Button'
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
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
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
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Knowledge collections</caption>
        <thead className="bg-neutral-50 dark:bg-neutral-900/60">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Collection
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Documents
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Created
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {collections.map((collection) => (
            <tr key={collection.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
              <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {collection.name}
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {collection.document_count}
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {formatCollectionDate(collection.created_at)}
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" size="sm" onClick={() => onView(collection)}>
                    View
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => onRename(collection)}>
                    Rename
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => onArchive(collection)}>
                    Archive
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
