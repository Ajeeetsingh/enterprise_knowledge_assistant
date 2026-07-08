import { type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { cn } from '@/utils/cn'

import {
  CONVERSATION_RENAME_API_AVAILABLE,
  MAX_CONVERSATION_TITLE_LENGTH,
  RENAME_UNAVAILABLE_MESSAGE,
} from '../constants'
import { conversationDisplayTitle, type Conversation } from '../types'

export interface RenameConversationModalProps {
  conversation: Conversation | null
  isOpen: boolean
  isSaving: boolean
  error: string | null
  onClose: () => void
  onSave: (title: string) => void
}

function validateTitle(title: string): string | null {
  const trimmed = title.trim()
  if (!trimmed) return 'Title is required.'
  if (trimmed.length > MAX_CONVERSATION_TITLE_LENGTH) {
    return `Title must not exceed ${MAX_CONVERSATION_TITLE_LENGTH} characters.`
  }
  return null
}

export default function RenameConversationModal({
  conversation,
  isOpen,
  isSaving,
  error,
  onClose,
  onSave,
}: RenameConversationModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [title, setTitle] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && conversation) {
      setTitle(conversation.title?.trim() || conversationDisplayTitle(conversation))
      setFieldError(null)
    }
  }, [isOpen, conversation])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLInputElement>('input')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !conversation) return null

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validationError = validateTitle(title)
    if (validationError) {
      setFieldError(validationError)
      return
    }
    setFieldError(null)
    onSave(title.trim())
  }

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
        className={cn(
          'w-full max-w-md rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Rename conversation
        </h2>

        {!CONVERSATION_RENAME_API_AVAILABLE && (
          <p className="mt-2 text-sm text-warning-700 dark:text-warning-500" role="note">
            {RENAME_UNAVAILABLE_MESSAGE}
          </p>
        )}

        <form className="mt-4 flex flex-col gap-4" onSubmit={handleSubmit}>
          <Input
            label="Title"
            value={title}
            disabled={isSaving}
            maxLength={MAX_CONVERSATION_TITLE_LENGTH}
            onChange={(event) => {
              setTitle(event.target.value)
              if (fieldError) setFieldError(null)
            }}
            {...(fieldError ? { error: fieldError } : {})}
          />

          {error && (
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" disabled={isSaving} onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving} disabled={isSaving}>
              Save
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
