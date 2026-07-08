import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

import { formatCollectionDate, type AdminCollection } from '../types'

export interface CollectionDetailsModalProps {
  isOpen: boolean
  collection: AdminCollection | null
  isLoading?: boolean
  error?: string | null
  onClose: () => void
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[10rem_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</dt>
      <dd className="break-all text-sm text-neutral-900 dark:text-neutral-100">{value}</dd>
    </div>
  )
}

export default function CollectionDetailsModal({
  isOpen,
  collection,
  isLoading = false,
  error = null,
  onClose,
}: CollectionDetailsModalProps) {
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
    if (isOpen) dialogRef.current?.focus()
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
            Collection Details
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        {isLoading && (
          <div className="mt-8 flex justify-center" role="status" aria-live="polite">
            <Spinner size="md" label="Loading collection details" />
          </div>
        )}

        {!isLoading && error && (
          <p role="alert" className="mt-6 text-sm text-error-500 dark:text-error-400">
            {error}
          </p>
        )}

        {!isLoading && !error && collection && (
          <dl className="mt-6 space-y-4">
            <MetadataRow label="Collection Name" value={collection.name} />
            <MetadataRow label="Description" value={collection.description ?? '—'} />
            <MetadataRow label="Document Count" value={String(collection.document_count)} />
            <MetadataRow label="Created Date" value={formatCollectionDate(collection.created_at)} />
            <MetadataRow label="Updated Date" value={formatCollectionDate(collection.updated_at)} />
            <MetadataRow label="Collection ID" value={collection.id} />
          </dl>
        )}
      </div>
    </div>
  )
}
