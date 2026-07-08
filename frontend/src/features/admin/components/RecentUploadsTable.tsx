import EmptyState from '@/components/ui/EmptyState'
import Spinner from '@/components/ui/Spinner'

import type { AdminDocumentRow } from '../utils/documentFilters'
import { mapVisibilityDisplay } from '../utils/documentFilters'
import { formatRelativeUploadedAt, getUploadDisplayStatus } from '../utils/uploadStatus'
import UploadStatusBadge from './UploadStatusBadge'

export interface RecentUploadsTableProps {
  uploads: AdminDocumentRow[]
  isLoading: boolean
  isRefreshing?: boolean
}

export default function RecentUploadsTable({
  uploads,
  isLoading,
  isRefreshing = false,
}: RecentUploadsTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading recent uploads">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  if (uploads.length === 0) {
    return (
      <EmptyState
        title="No recent uploads"
        description="Uploaded documents will appear here with processing status."
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-4 py-3 dark:border-neutral-700 dark:bg-neutral-900/60">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          Recent Uploads
        </h3>
        {isRefreshing && (
          <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
            <Spinner size="sm" label="Refreshing upload status" />
            Refreshing status…
          </div>
        )}
      </div>

      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Recent document uploads</caption>
        <thead className="bg-neutral-50 dark:bg-neutral-900/60">
          <tr>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Filename
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
              Uploaded
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Visibility
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {uploads.map((upload) => {
            const displayStatus = getUploadDisplayStatus(upload.status)

            return (
              <tr key={upload.document_id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
                <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {upload.filename}
                </td>
                <td className="px-4 py-3">
                  <UploadStatusBadge status={displayStatus} />
                  {displayStatus === 'FAILED' && (
                    <p className="mt-1 text-xs text-error-500 dark:text-error-400">
                      Processing failed. Select the file again to retry.
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {formatRelativeUploadedAt(upload.uploaded_at)}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {mapVisibilityDisplay(upload.visibility)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
