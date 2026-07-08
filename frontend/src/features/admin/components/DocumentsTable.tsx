import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'
import DocumentStatusBadge from '@/features/documents/components/DocumentStatusBadge'
import { formatUploadedAt } from '@/features/documents/types'

import type { AdminDocumentRow } from '../utils/documentFilters'
import { getDocumentType, mapVisibilityDisplay } from '../utils/documentFilters'

export interface DocumentsTableProps {
  documents: AdminDocumentRow[]
  isLoading: boolean
  onView: (document: AdminDocumentRow) => void
  onDelete: (document: AdminDocumentRow) => void
}

export default function DocumentsTable({
  documents,
  isLoading,
  onView,
  onDelete,
}: DocumentsTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading documents">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <EmptyState
        title="No documents found"
        description="Try adjusting your search or filters, or upload documents from the employee documents page."
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Enterprise documents</caption>
        <thead className="bg-neutral-50 dark:bg-neutral-900/60">
          <tr>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Name
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Type
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Visibility
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Created Date
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {documents.map((document) => (
            <tr key={document.document_id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
              <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {document.filename}
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {getDocumentType(document.filename)}
              </td>
              <td className="px-4 py-3">
                <DocumentStatusBadge status={document.status} />
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {mapVisibilityDisplay(document.visibility)}
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {formatUploadedAt(document.uploaded_at)}
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" size="sm" onClick={() => onView(document)}>
                    View
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => onDelete(document)}>
                    Delete
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
