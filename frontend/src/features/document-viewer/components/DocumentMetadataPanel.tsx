import type { DocumentDetail } from '@/features/documents/types'
import DocumentStatusBadge from '@/features/documents/components/DocumentStatusBadge'
import { cn } from '@/utils/cn'

import { getViewerMetadataFields } from '../utils/metadataDisplay'

export interface DocumentMetadataPanelProps {
  detail: DocumentDetail
  pageCount: number | null
  className?: string
}

export default function DocumentMetadataPanel({
  detail,
  pageCount,
  className,
}: DocumentMetadataPanelProps) {
  const fields = getViewerMetadataFields({
    document_id: detail.document_id,
    filename: detail.filename,
    file_size: detail.file_size,
    status: detail.status,
    uploaded_at: detail.uploaded_at,
    pageCount,
  })

  return (
    <div className={cn('viewer-metadata', className)}>
      <div className="viewer-metadata-hero">
        <p className="viewer-metadata-filename" title={detail.filename}>
          {detail.filename}
        </p>
        <div className="mt-2">
          <DocumentStatusBadge status={detail.status} />
        </div>
      </div>

      <dl className="viewer-metadata-list">
        {fields.map((field) => (
          <div key={field.label} className="viewer-metadata-row">
            <dt className="viewer-metadata-label">{field.label}</dt>
            <dd
              className={cn(
                'viewer-metadata-value',
                'mono' in field && field.mono && 'font-mono text-xs break-all',
              )}
              title={'hint' in field ? field.hint : undefined}
            >
              {field.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
