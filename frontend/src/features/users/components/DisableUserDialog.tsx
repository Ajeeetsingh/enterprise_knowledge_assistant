import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'

import type { User } from '../types'

export interface DisableUserDialogProps {
  targetUser: User | null
  isOpen: boolean
  isDisabling: boolean
  error: string | null
  onClose: () => void
  onConfirm: () => void
}

export default function DisableUserDialog({
  targetUser,
  isOpen,
  isDisabling,
  error,
  onClose,
  onConfirm,
}: DisableUserDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isDisabling) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isDisabling, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !targetUser) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isDisabling) onClose()
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
          Disable user?
        </h2>
        <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          This will deactivate <strong>{targetUser.full_name}</strong> ({targetUser.email}).
          They will no longer be able to sign in until an administrator reactivates the account.
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
            disabled={isDisabling}
            data-autofocus
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            isLoading={isDisabling}
            disabled={isDisabling}
            onClick={onConfirm}
          >
            Disable user
          </Button>
        </div>
      </div>
    </div>
  )
}
