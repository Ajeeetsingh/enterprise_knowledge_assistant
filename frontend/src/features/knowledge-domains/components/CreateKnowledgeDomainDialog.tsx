import { type FormEvent, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { cn } from '@/utils/cn'

export interface CreateKnowledgeDomainDialogProps {
  isOpen: boolean
  isSubmitting: boolean
  error: string | null
  onClose: () => void
  onSubmit: (input: { name: string; description: string }) => void
}

/**
 * Create-domain modal — always portaled to document.body so it never nests
 * inside a parent <form> (e.g. Upload Documents).
 */
export default function CreateKnowledgeDomainDialog({
  isOpen,
  isSubmitting,
  error,
  onClose,
  onSubmit,
}: CreateKnowledgeDomainDialogProps) {
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

    // Capture phase + stopImmediatePropagation so parent dialogs never see Escape.
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopImmediatePropagation()
      if (!isSubmitting) onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown, true)
    return () => window.document.removeEventListener('keydown', handleKeyDown, true)
  }, [isOpen, isSubmitting, onClose])

  if (!isOpen) return null

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    event.stopPropagation()
    const cleaned = name.trim()
    if (!cleaned) {
      setFieldError('Domain name is required.')
      return
    }
    setFieldError(null)
    onSubmit({ name: cleaned, description: description.trim() })
  }

  function handleBackdropPointerDown() {
    if (!isSubmitting) onClose()
  }

  const modal = (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 px-4"
      data-testid="create-knowledge-domain-backdrop"
      onPointerDown={(event) => {
        // Only the backdrop itself — not the dialog panel.
        if (event.target === event.currentTarget) {
          handleBackdropPointerDown()
        }
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="create-knowledge-domain-dialog"
        className={cn(
          'w-full max-w-md rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Create Knowledge Domain
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Add a domain that documents can be assigned to during upload.
        </p>

        <form
          className="mt-4 space-y-4"
          onSubmit={handleSubmit}
          // Isolated from any ancestor form in the React tree.
        >
          <Input
            label="Domain Name"
            value={name}
            disabled={isSubmitting}
            {...(fieldError ? { error: fieldError } : {})}
            onChange={(event) => {
              setName(event.target.value)
              if (fieldError) setFieldError(null)
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

  return createPortal(modal, document.body)
}
