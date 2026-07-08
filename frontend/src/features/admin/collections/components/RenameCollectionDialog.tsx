import { type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { cn } from '@/utils/cn'

import type { AdminCollection } from '../types'
import { validateCollectionName } from '../utils/collectionFilters'

export interface RenameCollectionDialogProps {
  collection: AdminCollection | null
  isOpen: boolean
  confirmOpen: boolean
  isSubmitting: boolean
  error: string | null
  onClose: () => void
  onApply: (name: string) => void
  onConfirm: () => void
  onBack: () => void
}

export default function RenameCollectionDialog({
  collection,
  isOpen,
  confirmOpen,
  isSubmitting,
  error,
  onClose,
  onApply,
  onConfirm,
  onBack,
}: RenameCollectionDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [name, setName] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !collection) return
    setName(collection.name)
    setFieldError(null)
  }, [isOpen, collection])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isSubmitting) onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown)
    return () => window.document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isSubmitting, onClose])

  if (!isOpen || !collection) return null

  function handleApply(event: FormEvent) {
    event.preventDefault()
    const validationError = validateCollectionName(name)
    if (validationError) {
      setFieldError(validationError)
      return
    }

    if (name.trim() === collection!.name) {
      onClose()
      return
    }

    setFieldError(null)
    onApply(name.trim())
  }

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
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className={cn(
          'w-full max-w-md rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        {!confirmOpen ? (
          <>
            <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Rename Collection
            </h2>
            <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Update the display name for <strong>{collection.name}</strong>.
            </p>

            <form className="mt-4 space-y-4" onSubmit={handleApply}>
              <Input
                label="Collection name"
                value={name}
                disabled={isSubmitting}
                {...(fieldError ? { error: fieldError } : {})}
                onChange={(event) => {
                  setName(event.target.value)
                  setFieldError(validateCollectionName(event.target.value))
                }}
              />

              {error && (
                <p role="alert" className="text-sm text-error-500 dark:text-error-400">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-2">
                <Button type="button" variant="secondary" disabled={isSubmitting} onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  Continue
                </Button>
              </div>
            </form>
          </>
        ) : (
          <>
            <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Confirm rename?
            </h2>
            <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Rename <strong>{collection.name}</strong> to <strong>{name.trim()}</strong>.
            </p>

            {error && (
              <p role="alert" className="mt-3 text-sm text-error-500 dark:text-error-400">
                {error}
              </p>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="secondary" disabled={isSubmitting} onClick={onBack}>
                Back
              </Button>
              <Button
                type="button"
                isLoading={isSubmitting}
                disabled={isSubmitting}
                onClick={onConfirm}
              >
                Confirm
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
