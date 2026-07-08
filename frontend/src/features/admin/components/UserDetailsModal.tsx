import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import Badge from '@/components/ui/Badge'
import { formatCreatedAt, formatUserRoles, type User } from '@/features/users/types'
import { getUserPermissions } from '@/types/permissions'
import { cn } from '@/utils/cn'

import { getPrimaryRole } from '../utils/userFilters'

export interface UserDetailsModalProps {
  isOpen: boolean
  user: User | null
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

export default function UserDetailsModal({
  isOpen,
  user,
  isLoading,
  error,
  onClose,
  onRetry,
}: UserDetailsModalProps) {
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

  const permissions = user
    ? getUserPermissions({
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        roles: user.roles,
        is_active: user.is_active,
        is_superuser: user.is_superuser,
      })
    : []

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
            User Details
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        {isLoading && (
          <div className="mt-8 flex justify-center" role="status" aria-live="polite">
            <Spinner size="md" label="Loading user details" />
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

        {!isLoading && !error && user && (
          <dl className="mt-6 space-y-4">
            <MetadataRow label="Name" value={user.full_name} />
            <MetadataRow label="Email" value={user.email} />
            <MetadataRow label="Role" value={formatUserRoles(user.roles) || getPrimaryRole(user.roles)} />
            <div className="grid gap-1 sm:grid-cols-[10rem_1fr] sm:gap-4">
              <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Status</dt>
              <dd>
                <Badge variant={user.is_active ? 'success' : 'error'}>
                  {user.is_active ? 'Active' : 'Disabled'}
                </Badge>
              </dd>
            </div>
            <MetadataRow label="Created Date" value={formatCreatedAt(user.created_at)} />
            <MetadataRow label="User ID" value={user.id} />
            <div className="grid gap-2 sm:grid-cols-[10rem_1fr] sm:gap-4">
              <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
                Permissions
              </dt>
              <dd className="flex flex-wrap gap-2">
                {permissions.length > 0 ? (
                  permissions.map((permission) => (
                    <Badge key={permission} variant="info">
                      {permission}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-neutral-600 dark:text-neutral-300">—</span>
                )}
              </dd>
            </div>
          </dl>
        )}
      </div>
    </div>
  )
}
