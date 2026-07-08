import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import DocumentStatusBadge from '@/features/documents/components/DocumentStatusBadge'
import { VISIBILITY_NOT_IN_LIST_API } from '@/features/documents/constants'
import type { DocumentDetail } from '@/features/documents/types'
import { formatUploadedAt } from '@/features/documents/types'
import { cn } from '@/utils/cn'

import { formatFileSize, mapVisibilityDisplay } from '../utils/documentFilters'

export interface DocumentDetailsModalProps {
  isOpen: boolean
  documentDetail: DocumentDetail | null
  isLoading: boolean
  error: string | null
  onClose: () => void
  onRetry?: () => void
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[10rem_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</dt>
      <dd className="break-all text-sm text-neutral-900 dark:text-neutral-100">{value}</dd>
    </div>
  )
}

export default function DocumentDetailsModal({
  isOpen,
  documentDetail,
  isLoading,
  error,
  onClose,
  onRetry,
}: DocumentDetailsModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown)
    return () => window.document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.focus()
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            Document Details
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        {isLoading && (
          <div className="mt-8 flex justify-center" role="status" aria-live="polite">
            <Spinner size="md" label="Loading document metadata" />
          </div>
        )}

        {!isLoading && error && (
          <div className="mt-6 flex flex-col gap-3">
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
            {onRetry && (
              <Button variant="secondary" size="sm" onClick={onRetry}>
                Retry
              </Button>
            )}
          </div>
        )}

        {!isLoading && !error && documentDetail && (
          <dl className="mt-6 space-y-4">
            <MetadataRow label="Name" value={documentDetail.filename} />
            <MetadataRow label="Document Type" value={documentDetail.content_type} />
            <div className="grid gap-1 sm:grid-cols-[10rem_1fr] sm:gap-4">
              <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Status</dt>
              <dd>
                <DocumentStatusBadge status={documentDetail.status} />
              </dd>
            </div>
            <MetadataRow label="Visibility" value={mapVisibilityDisplay(undefined)} />
            <p className="text-xs text-neutral-500 dark:text-neutral-400">{VISIBILITY_NOT_IN_LIST_API}</p>
            <MetadataRow label="Version" value="—" />
            <MetadataRow label="Created Date" value={formatUploadedAt(documentDetail.uploaded_at)} />
            <MetadataRow label="Updated Date" value="—" />
            <MetadataRow label="Checksum" value={documentDetail.checksum} />
            <MetadataRow label="Document ID" value={documentDetail.document_id} />
            <MetadataRow label="File Size" value={formatFileSize(documentDetail.file_size)} />
            <MetadataRow label="Uploaded By" value={documentDetail.uploaded_by} />
          </dl>
        )}
      </div>
    </div>
  )
}
