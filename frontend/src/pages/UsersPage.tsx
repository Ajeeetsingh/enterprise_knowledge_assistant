import { useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/contexts/ToastContext'
import {
  CreateUserDialog,
  DisableUserDialog,
  UserTable,
} from '@/features/users/components'
import { useCreateUser } from '@/features/users/hooks/useCreateUser'
import { useDisableUser } from '@/features/users/hooks/useDisableUser'
import { useRoles } from '@/features/users/hooks/useRoles'
import { useUsers } from '@/features/users/hooks/useUsers'
import type { User } from '@/features/users/types'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

export default function UsersPage() {
  const { showSuccess, showError } = useToast()
  const [createOpen, setCreateOpen] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [disableTarget, setDisableTarget] = useState<User | null>(null)
  const [disableError, setDisableError] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useUsers()
  const { data: rolesData, isLoading: rolesLoading } = useRoles()
  const createUser = useCreateUser()
  const disableUser = useDisableUser()

  const users = data?.users ?? []
  const roles = rolesData?.roles ?? []

  function openCreate() {
    setCreateError(null)
    setCreateOpen(true)
  }

  function closeCreate() {
    if (createUser.isPending) return
    setCreateOpen(false)
    setCreateError(null)
  }

  async function handleCreate(input: {
    full_name: string
    email: string
    password: string
    role: string
  }) {
    setCreateError(null)
    try {
      await createUser.mutateAsync(input)
      setCreateOpen(false)
      showSuccess('User created successfully.')
    } catch (createFailure) {
      const message = getApiErrorMessage(createFailure)
      setCreateError(message)
      showError(message)
    }
  }

  function openDisable(user: User) {
    setDisableError(null)
    setDisableTarget(user)
  }

  function closeDisable() {
    if (disableUser.isPending) return
    setDisableTarget(null)
    setDisableError(null)
  }

  async function handleDisableConfirm() {
    if (!disableTarget) return
    setDisableError(null)
    try {
      await disableUser.mutateAsync(disableTarget.id)
      setDisableTarget(null)
      showSuccess('User disabled successfully.')
    } catch (disableFailure) {
      const message = getApiErrorMessage(disableFailure)
      setDisableError(message)
      showError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Users</h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Manage enterprise accounts, roles, and access status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            <span className="font-medium">{users.length}</span> user{users.length === 1 ? '' : 's'}
          </p>
          <Button onClick={openCreate}>Create user</Button>
        </div>
      </div>

      {isError && (
        <Card>
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {resolveErrorMessage(error)}
          </p>
        </Card>
      )}

      {!isError && !isLoading && users.length === 0 ? (
        <Card>
          <EmptyState
            title="No users found"
            description="Create the first user account to get started."
            action={
              <Button size="sm" onClick={openCreate}>
                Create user
              </Button>
            }
          />
        </Card>
      ) : (
        <UserTable users={users} isLoading={isLoading} onDisable={openDisable} />
      )}

      <CreateUserDialog
        isOpen={createOpen}
        isSubmitting={createUser.isPending}
        roles={roles}
        rolesLoading={rolesLoading}
        error={createError}
        onClose={closeCreate}
        onSubmit={(input) => void handleCreate(input)}
      />

      <DisableUserDialog
        targetUser={disableTarget}
        isOpen={disableTarget !== null}
        isDisabling={disableUser.isPending}
        error={disableError}
        onClose={closeDisable}
        onConfirm={() => void handleDisableConfirm()}
      />
    </div>
  )
}
