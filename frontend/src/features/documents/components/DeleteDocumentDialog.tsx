import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'

import type { Document } from '../types'

export interface DeleteDocumentDialogProps {
  targetDocument: Document | null
  isOpen: boolean
  isDeleting: boolean
  error: string | null
  onClose: () => void
  onConfirm: () => void
}

export default function DeleteDocumentDialog({
  targetDocument,
  isOpen,
  isDeleting,
  error,
  onClose,
  onConfirm,
}: DeleteDocumentDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isDeleting) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isDeleting, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !targetDocument) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isDeleting) onClose()
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
          Delete document?
        </h2>
        <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          This will permanently remove <strong>{targetDocument.filename}</strong> from the knowledge
          base, including indexed content. This action cannot be undone.
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
            disabled={isDeleting}
            data-autofocus
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            isLoading={isDeleting}
            disabled={isDeleting}
            onClick={onConfirm}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}
