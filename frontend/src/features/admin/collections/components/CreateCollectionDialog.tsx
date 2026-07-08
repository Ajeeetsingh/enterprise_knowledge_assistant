import { type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { cn } from '@/utils/cn'

import { validateCollectionName } from '../utils/collectionFilters'

export interface CreateCollectionDialogProps {
  isOpen: boolean
  isSubmitting: boolean
  error: string | null
  onClose: () => void
  onSubmit: (input: { name: string; description: string }) => void
}

export default function CreateCollectionDialog({
  isOpen,
  isSubmitting,
  error,
  onClose,
  onSubmit,
}: CreateCollectionDialogProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) {
      setName('')
      setDescription('')
      setFieldError(null)
      return
    }

    dialogRef.current?.querySelector<HTMLInputElement>('input')?.focus()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isSubmitting) onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown)
    return () => window.document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isSubmitting, onClose])

  if (!isOpen) return null

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validationError = validateCollectionName(name)
    if (validationError) {
      setFieldError(validationError)
      return
    }

    setFieldError(null)
    onSubmit({ name: name.trim(), description: description.trim() })
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
        className={cn(
          'w-full max-w-lg rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Create Collection
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Organize related documents into a logical knowledge group.
        </p>

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
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

          <Input
            label="Description"
            value={description}
            disabled={isSubmitting}
            hint="Optional"
            onChange={(event) => setDescription(event.target.value)}
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
            <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>
              Create
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
