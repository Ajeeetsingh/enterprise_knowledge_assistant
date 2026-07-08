import Card from '@/components/ui/Card'
import type { DocumentUploadResponse } from '@/features/documents/types'

import UploadStatusBadge from './UploadStatusBadge'
import { getUploadDisplayStatus } from '../utils/uploadStatus'

export interface UploadStatusPanelProps {
  isUploading: boolean
  lastUpload: DocumentUploadResponse | null
}

export default function UploadStatusPanel({ isUploading, lastUpload }: UploadStatusPanelProps) {
  if (!isUploading && !lastUpload) return null

  const status = lastUpload
    ? getUploadDisplayStatus(lastUpload.status, isUploading)
    : 'UPLOADING'

  const statusMessage =
    status === 'UPLOADING'
      ? 'Your document is being uploaded.'
      : status === 'PROCESSING'
        ? 'Upload complete. Document is processing.'
        : status === 'READY'
          ? 'Upload complete. Document is ready for search.'
          : 'Upload failed or processing failed. Select the file again to retry.'

  return (
    <Card title="Upload Status">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          {lastUpload && (
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              {lastUpload.filename}
            </p>
          )}
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{statusMessage}</p>
        </div>
        <UploadStatusBadge status={status} />
      </div>
    </Card>
  )
}
