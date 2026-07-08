import { useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import { formatUserRoles, type Role, type User } from '@/features/users/types'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import { canChangeUserRole, getPrimaryRole } from '../utils/userFilters'

export interface UserRoleSelectorProps {
  user: User | null
  roles: Role[]
  isOpen: boolean
  isUpdating: boolean
  error: string | null
  onClose: () => void
  onConfirm: (newRole: string) => void
}

export default function UserRoleSelector({
  user,
  roles,
  isOpen,
  isUpdating,
  error,
  onClose,
  onConfirm,
}: UserRoleSelectorProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const { user: currentUser } = useAuth()
  const [selectedRole, setSelectedRole] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)

  useEffect(() => {
    if (!isOpen || !user) return
    setSelectedRole(getPrimaryRole(user.roles) === '—' ? roles[0]?.name ?? '' : user.roles[0] ?? '')
    setConfirmOpen(false)
  }, [isOpen, user, roles])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isUpdating) onClose()
    }

    window.document.addEventListener('keydown', handleKeyDown)
    return () => window.document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isUpdating, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLSelectElement>('select')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !user) return null

  const roleCheck = canChangeUserRole(user, currentUser, selectedRole)
  const currentRoleLabel = formatUserRoles(user.roles) || getPrimaryRole(user.roles)

  function handleApplyClick() {
    if (!roleCheck.allowed) return
    if (selectedRole === user!.roles[0] && user!.roles.length === 1) return
    setConfirmOpen(true)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isUpdating) onClose()
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
              Assign Role
            </h2>
            <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Change the primary role for <strong>{user.full_name}</strong>. Current role:{' '}
              {currentRoleLabel}.
            </p>

            <div className="mt-4">
              <label
                htmlFor="admin-user-role-select"
                className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-200"
              >
                Role
              </label>
              <select
                id="admin-user-role-select"
                value={selectedRole}
                disabled={isUpdating}
                onChange={(event) => setSelectedRole(event.target.value)}
                className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-50 dark:focus:ring-offset-neutral-900"
              >
                {roles.map((role) => (
                  <option key={role.id} value={role.name}>
                    {role.name}
                  </option>
                ))}
              </select>
            </div>

            {!roleCheck.allowed && roleCheck.reason && (
              <p role="alert" className="mt-3 text-sm text-error-500 dark:text-error-400">
                {roleCheck.reason}
              </p>
            )}

            {error && (
              <p role="alert" className="mt-3 text-sm text-error-500 dark:text-error-400">
                {error}
              </p>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="secondary" disabled={isUpdating} onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="button"
                disabled={isUpdating || !selectedRole || !roleCheck.allowed}
                onClick={handleApplyClick}
              >
                Apply
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Confirm role change?
            </h2>
            <p id={descriptionId} className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              Assign <strong>{selectedRole}</strong> to {user.full_name}. This updates the user&apos;s
              platform access immediately.
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
                disabled={isUpdating}
                onClick={() => setConfirmOpen(false)}
              >
                Back
              </Button>
              <Button
                type="button"
                isLoading={isUpdating}
                disabled={isUpdating}
                onClick={() => onConfirm(selectedRole)}
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
