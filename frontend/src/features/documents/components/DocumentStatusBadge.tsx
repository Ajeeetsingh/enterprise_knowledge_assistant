import Badge from '@/components/ui/Badge'

import { getStatusDisplay, getStatusLabel } from '../types'

export interface DocumentStatusBadgeProps {
  status: string
}

const DISPLAY_VARIANTS = {
  PROCESSING: 'warning',
  READY: 'success',
  FAILED: 'error',
  DELETED: 'info',
} as const

export default function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const display = getStatusDisplay(status)
  const label = getStatusLabel(status)

  return (
    <Badge variant={DISPLAY_VARIANTS[display]} title={label}>
      {label}
    </Badge>
  )
}
