import ActionButton from '@/components/ui/ActionButton'
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
            className="h-12 animate-pulse rounded-md bg-overlay"
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
    <div className="data-table-shell">
      <table className="data-table">
        <caption className="sr-only">Enterprise documents</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Type</th>
            <th scope="col">Status</th>
            <th scope="col">Visibility</th>
            <th scope="col">Created Date</th>
            <th scope="col" className="text-right">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.document_id} className="interactive-row">
              <td className="font-medium">{document.filename}</td>
              <td className="text-muted">{getDocumentType(document.filename)}</td>
              <td>
                <DocumentStatusBadge status={document.status} />
              </td>
              <td className="text-muted">{mapVisibilityDisplay(document.visibility)}</td>
              <td className="text-muted">{formatUploadedAt(document.uploaded_at)}</td>
              <td>
                <div className="flex justify-end gap-2">
                  <ActionButton onClick={() => onView(document)}>View</ActionButton>
                  <ActionButton destructive onClick={() => onDelete(document)}>
                    Delete
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
