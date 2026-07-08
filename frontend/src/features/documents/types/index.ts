/**
 * Document types — aligned with backend document management API (Phase 9.3).
 */

export enum DocumentStatus {
  Uploaded = 'uploaded',
  Validated = 'validated',
  Stored = 'stored',
  Processing = 'processing',
  Indexed = 'indexed',
  Searchable = 'searchable',
  Failed = 'failed',
  RetryPending = 'retry_pending',
  Deleted = 'deleted',
}

/** Stored on documents in the backend; not yet exposed in list/detail API responses. */
export enum DocumentVisibility {
  Public = 'public',
  Restricted = 'restricted',
  Private = 'private',
}

export interface Document {
  document_id: string
  filename: string
  status: DocumentStatus | string
  uploaded_at: string
  uploaded_by: string
}

export interface DocumentDetail extends Document {
  content_type: string
  file_size: number
  checksum: string
}

export interface PaginatedDocumentResponse {
  items: Document[]
  total: number
  limit: number
  offset: number
}

export interface DocumentUploadRequest {
  file: File
}

export interface DocumentUploadResponse {
  document_id: string
  filename: string
  status: DocumentStatus | string
  message: string
}

export interface DocumentDeleteResponse {
  document_id: string
  status: DocumentStatus | string
  message: string
}

/** UI grouping for lifecycle badges (maps backend statuses). */
export type DocumentStatusDisplay = 'PROCESSING' | 'READY' | 'FAILED' | 'DELETED'

export function getStatusDisplay(status: string): DocumentStatusDisplay {
  switch (status) {
    case DocumentStatus.Deleted:
      return 'DELETED'
    case DocumentStatus.Searchable:
    case DocumentStatus.Indexed:
      return 'READY'
    case DocumentStatus.Failed:
    case DocumentStatus.RetryPending:
      return 'FAILED'
    default:
      return 'PROCESSING'
  }
}

export function getStatusLabel(status: string): string {
  switch (getStatusDisplay(status)) {
    case 'DELETED':
      return 'Deleted'
    case 'READY':
      return 'Ready'
    case 'FAILED':
      return 'Failed'
    default:
      return 'Processing'
  }
}

export function formatUploadedAt(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
