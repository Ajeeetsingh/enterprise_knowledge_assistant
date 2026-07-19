import { DocumentStatus } from '@/features/documents/types'

import { DEFAULT_EMBEDDING_MODEL } from '../constants'
import { formatFileSize } from './formatFileSize'

export function getIndexingStatusLabel(status: string): string {
  switch (status) {
    case DocumentStatus.Searchable:
    case DocumentStatus.Indexed:
      return 'Indexed'
    case DocumentStatus.Failed:
    case DocumentStatus.RetryPending:
      return 'Failed'
    default:
      return 'In progress'
  }
}

export function getViewerMetadataFields(detail: {
  document_id: string
  filename: string
  file_size: number
  status: string
  uploaded_at: string
  pageCount: number | null
}) {
  return [
    { label: 'File name', value: detail.filename },
    { label: 'Upload date', value: new Date(detail.uploaded_at).toLocaleString() },
    { label: 'Pages', value: detail.pageCount != null ? String(detail.pageCount) : '—' },
    { label: 'File size', value: formatFileSize(detail.file_size) },
    { label: 'Processing status', value: detail.status },
    { label: 'Indexing status', value: getIndexingStatusLabel(detail.status) },
    { label: 'Number of chunks', value: '—', hint: 'Not exposed by document API yet' },
    { label: 'Embedding model', value: DEFAULT_EMBEDDING_MODEL },
    { label: 'Last indexed', value: '—', hint: 'Not exposed by document API yet' },
    { label: 'Document ID', value: detail.document_id, mono: true },
  ] as const
}