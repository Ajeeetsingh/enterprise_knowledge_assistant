import Badge from '@/components/ui/Badge'

import type { UploadDisplayStatus } from '../utils/uploadStatus'

export interface UploadStatusBadgeProps {
  status: UploadDisplayStatus
}

const STATUS_LABELS: Record<UploadDisplayStatus, string> = {
  UPLOADING: 'Uploading',
  PROCESSING: 'Processing',
  READY: 'Ready',
  FAILED: 'Failed',
}

const STATUS_VARIANTS = {
  UPLOADING: 'warning',
  PROCESSING: 'warning',
  READY: 'success',
  FAILED: 'error',
} as const

export default function UploadStatusBadge({ status }: UploadStatusBadgeProps) {
  return (
    <Badge variant={STATUS_VARIANTS[status]} title={status}>
      {STATUS_LABELS[status]}
    </Badge>
  )
}
