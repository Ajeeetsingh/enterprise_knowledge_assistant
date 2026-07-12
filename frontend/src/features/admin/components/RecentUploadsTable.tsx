import EmptyState from '@/components/ui/EmptyState'
import Spinner from '@/components/ui/Spinner'
import {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
  DataTableShell,
} from '@/components/ui/DataTable'

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
          <div key={index} className="h-12 animate-pulse rounded-md bg-overlay" />
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
    <DataTableShell>
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Recent Uploads</h3>
        {isRefreshing && (
          <div className="flex items-center gap-2 text-xs text-muted">
            <Spinner size="sm" label="Refreshing upload status" />
            Refreshing status…
          </div>
        )}
      </div>

      <table className="data-table">
        <caption className="sr-only">Recent document uploads</caption>
        <DataTableHead>
          <DataTableRow interactive={false}>
            <DataTableHeaderCell>Filename</DataTableHeaderCell>
            <DataTableHeaderCell>Status</DataTableHeaderCell>
            <DataTableHeaderCell>Uploaded</DataTableHeaderCell>
            <DataTableHeaderCell>Visibility</DataTableHeaderCell>
          </DataTableRow>
        </DataTableHead>
        <DataTableBody>
          {uploads.map((upload) => {
            const displayStatus = getUploadDisplayStatus(upload.status)

            return (
              <DataTableRow key={upload.document_id}>
                <DataTableCell className="font-medium">{upload.filename}</DataTableCell>
                <DataTableCell>
                  <UploadStatusBadge status={displayStatus} />
                  {displayStatus === 'FAILED' && (
                    <p className="mt-1 text-xs text-status-bad">
                      Processing failed. Select the file again to retry.
                    </p>
                  )}
                </DataTableCell>
                <DataTableCell muted>{formatRelativeUploadedAt(upload.uploaded_at)}</DataTableCell>
                <DataTableCell muted>{mapVisibilityDisplay(upload.visibility)}</DataTableCell>
              </DataTableRow>
            )
          })}
        </DataTableBody>
      </table>
    </DataTableShell>
  )
}
