import { useEffect, useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/contexts/ToastContext'
import {
  useRoles,
  useToggleUserStatus,
  useUpdateUserRole,
  useUser,
  useUsers,
} from '@/features/users/hooks'
import type { User } from '@/features/users/types'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

import { ADMIN_USERS_PAGE_SIZE } from '../constants/users'
import ToggleUserStatusDialog from '../components/ToggleUserStatusDialog'
import UserDetailsModal from '../components/UserDetailsModal'
import UserFilters from '../components/UserFilters'
import UserPagination from '../components/UserPagination'
import UserRoleSelector from '../components/UserRoleSelector'
import UsersTable from '../components/UsersTable'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import {
  applyUserFilters,
  paginateUsers,
  type UserFilterState,
} from '../utils/userFilters'

function resolveLoadError(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Unable to load users.'
}

const DEFAULT_FILTERS: UserFilterState = {
  role: 'ALL',
  status: 'ALL',
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const { showSuccess, showError } = useToast()
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<UserFilterState>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const [viewTargetId, setViewTargetId] = useState<string | null>(null)
  const [roleTarget, setRoleTarget] = useState<User | null>(null)
  const [roleError, setRoleError] = useState<string | null>(null)
  const [statusTarget, setStatusTarget] = useState<User | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)

  const debouncedSearch = useDebouncedValue(search, 300)

  const { data, isLoading, isError, error, refetch } = useUsers()
  const { data: rolesData } = useRoles()
  const updateUserRole = useUpdateUserRole()
  const toggleUserStatus = useToggleUserStatus()

  const {
    data: userDetail,
    isLoading: isDetailLoading,
    isError: isDetailError,
    error: detailError,
    refetch: refetchDetail,
  } = useUser(viewTargetId, viewTargetId !== null)

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, filters.role, filters.status])

  const filteredUsers = useMemo(() => {
    return applyUserFilters(data?.users ?? [], filters, debouncedSearch)
  }, [data?.users, filters, debouncedSearch])

  const pagination = useMemo(
    () => paginateUsers(filteredUsers, page, ADMIN_USERS_PAGE_SIZE),
    [filteredUsers, page],
  )

  function openView(user: User) {
    setViewTargetId(user.id)
  }

  function closeView() {
    setViewTargetId(null)
  }

  function openRoleDialog(user: User) {
    setRoleError(null)
    setRoleTarget(user)
  }

  function closeRoleDialog() {
    if (updateUserRole.isPending) return
    setRoleTarget(null)
    setRoleError(null)
  }

  async function handleRoleConfirm(newRole: string) {
    if (!roleTarget) return
    setRoleError(null)

    try {
      await updateUserRole.mutateAsync({
        userId: roleTarget.id,
        user: roleTarget,
        newRole,
      })
      setRoleTarget(null)
      showSuccess('User role updated successfully.')
    } catch (roleFailure) {
      const message = getApiErrorMessage(roleFailure) || 'Unable to update role.'
      setRoleError(message)
      showError(message)
    }
  }

  function openStatusDialog(user: User) {
    setStatusError(null)
    setStatusTarget(user)
  }

  function closeStatusDialog() {
    if (toggleUserStatus.isPending) return
    setStatusTarget(null)
    setStatusError(null)
  }

  async function handleStatusConfirm() {
    if (!statusTarget) return
    setStatusError(null)

    try {
      await toggleUserStatus.mutateAsync({
        user: statusTarget,
        enable: !statusTarget.is_active,
      })
      setStatusTarget(null)
      showSuccess(
        statusTarget.is_active ? 'User disabled successfully.' : 'User enabled successfully.',
      )
    } catch (statusFailure) {
      const message =
        getApiErrorMessage(statusFailure) ||
        (statusTarget.is_active ? 'Unable to disable user.' : 'Unable to enable user.')
      setStatusError(message)
      showError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            User Administration
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Manage platform access, roles, and account status for enterprise users.
          </p>
        </div>

        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          <span className="font-medium">{pagination.total}</span> user
          {pagination.total === 1 ? '' : 's'}
        </p>
      </div>

      <UserFilters
        filters={filters}
        onChange={setFilters}
        search={search}
        onSearchChange={setSearch}
      />

      {isError && (
        <Card>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {resolveLoadError(error)}
            </p>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              Retry
            </Button>
          </div>
        </Card>
      )}

      {!isError && (
        <>
          <UsersTable
            users={pagination.items}
            isLoading={isLoading}
            {...(currentUser?.id ? { currentUserId: currentUser.id } : {})}
            onView={openView}
            onManageRole={openRoleDialog}
            onToggleStatus={openStatusDialog}
          />

          {!isLoading && pagination.total > 0 && (
            <UserPagination
              page={pagination.page}
              totalPages={pagination.totalPages}
              totalResults={pagination.total}
              onPrevious={() => setPage((current) => Math.max(current - 1, 1))}
              onNext={() =>
                setPage((current) => Math.min(current + 1, pagination.totalPages))
              }
            />
          )}
        </>
      )}

      <UserDetailsModal
        isOpen={viewTargetId !== null}
        user={userDetail ?? null}
        isLoading={isDetailLoading}
        error={
          isDetailError ? getApiErrorMessage(detailError) || 'Unable to load user details.' : null
        }
        onClose={closeView}
        onRetry={() => void refetchDetail()}
      />

      <UserRoleSelector
        user={roleTarget}
        roles={rolesData?.roles ?? []}
        isOpen={roleTarget !== null}
        isUpdating={updateUserRole.isPending}
        error={roleError}
        onClose={closeRoleDialog}
        onConfirm={(newRole) => void handleRoleConfirm(newRole)}
      />

      <ToggleUserStatusDialog
        targetUser={statusTarget}
        {...(currentUser?.id ? { currentUserId: currentUser.id } : {})}
        isOpen={statusTarget !== null}
        isSubmitting={toggleUserStatus.isPending}
        error={statusError}
        onClose={closeStatusDialog}
        onConfirm={() => void handleStatusConfirm()}
      />
    </div>
  )
}
