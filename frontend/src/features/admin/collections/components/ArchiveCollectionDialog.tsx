import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'

import type { AdminCollection } from '../types'

export interface ArchiveCollectionDialogProps {
  collection: AdminCollection | null
  isOpen: boolean
  isSubmitting: boolean
  error: string | null
  onClose: () => void
  onConfirm: () => void
}

export default function ArchiveCollectionDialog({
  collection,
  isOpen,
  isSubmitting,
  error,
  onClose,
  onConfirm,
}: ArchiveCollectionDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isSubmitting) onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown)
    return () => window.document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isSubmitting, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !collection) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isSubmitting) onClose()
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className={cn(
          'w-full max-w-md rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Archive collection?
        </h2>
        <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          Archive <strong>{collection.name}</strong>. Documents remain in the knowledge base, but
          this collection will be hidden from active administration views.
        </p>

        {error && (
          <p role="alert" className="mt-3 text-sm text-error-500 dark:text-error-400">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={isSubmitting}
            data-autofocus
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            isLoading={isSubmitting}
            disabled={isSubmitting}
            onClick={onConfirm}
          >
            Archive
          </Button>
        </div>
      </div>
    </div>
  )
}
