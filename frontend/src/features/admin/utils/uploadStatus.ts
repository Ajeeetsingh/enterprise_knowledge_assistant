import { getStatusDisplay } from '@/features/documents/types'

export type UploadDisplayStatus = 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED'

export function getUploadDisplayStatus(
  status: string,
  isUploading = false,
): UploadDisplayStatus {
  if (isUploading) return 'UPLOADING'

  const display = getStatusDisplay(status)
  if (display === 'DELETED') return 'FAILED'
  if (display === 'READY') return 'READY'
  if (display === 'FAILED') return 'FAILED'
  return 'PROCESSING'
}

export function shouldPollRecentUploads(
  documents: Array<{ status: string }>,
): boolean {
  return documents.some((document) => getUploadDisplayStatus(document.status) === 'PROCESSING')
}

export function formatRelativeUploadedAt(value: string): string {
  const uploadedAt = new Date(value)
  const now = new Date()

  const isSameDay =
    uploadedAt.getFullYear() === now.getFullYear() &&
    uploadedAt.getMonth() === now.getMonth() &&
    uploadedAt.getDate() === now.getDate()

  if (isSameDay) return 'Today'

  const diffMs = now.getTime() - uploadedAt.getTime()
  const diffMinutes = Math.floor(diffMs / 60_000)

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes} min ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} hr ago`

  return uploadedAt.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
