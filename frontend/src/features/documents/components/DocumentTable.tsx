import { useNavigate } from 'react-router-dom'

import ActionButton from '@/components/ui/ActionButton'
import Button from '@/components/ui/Button'

import { VISIBILITY_NOT_IN_LIST_API } from '../constants'
import type { Document } from '../types'
import DocumentStatusBadge from './DocumentStatusBadge'

export interface DocumentTableProps {
  documents: Document[]
  isLoading: boolean
  onView?: (document: Document) => void
  onDownload?: (document: Document) => void
  onDelete: (document: Document) => void
}

export default function DocumentTable({
  documents,
  isLoading,
  onView,
  onDownload,
  onDelete,
}: DocumentTableProps) {
  const navigate = useNavigate()

  function handleView(document: Document) {
    if (onView) {
      onView(document)
      return
    }
    navigate(`/documents/${document.document_id}`)
  }

  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading documents">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Uploaded documents</caption>
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
              Status
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
              title={VISIBILITY_NOT_IN_LIST_API}
            >
              Visibility
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Uploaded At
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
              <td className="px-4 py-3">
                <DocumentStatusBadge status={document.status} />
              </td>
              <td
                className="px-4 py-3 text-sm text-neutral-500 dark:text-neutral-400"
                title={VISIBILITY_NOT_IN_LIST_API}
              >
                —
              </td>
              <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                {new Date(document.uploaded_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right">
                <div className="flex justify-end gap-2">
                  <ActionButton onClick={() => handleView(document)}>View</ActionButton>
                  {onDownload && (
                    <ActionButton onClick={() => onDownload(document)}>Download</ActionButton>
                  )}
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
