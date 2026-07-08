import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { formatCreatedAt, formatUserRoles, type User } from '@/features/users/types'

import { getDisableBlockReason, getPrimaryRole } from '../utils/userFilters'

export interface UsersTableProps {
  users: User[]
  isLoading: boolean
  currentUserId?: string
  onView: (user: User) => void
  onManageRole: (user: User) => void
  onToggleStatus: (user: User) => void
}

function AdminUserStatusBadge({ isActive }: { isActive: boolean }) {
  if (isActive) {
    return <Badge variant="success">Active</Badge>
  }

  return <Badge variant="error">Disabled</Badge>
}

export default function UsersTable({
  users,
  isLoading,
  currentUserId,
  onView,
  onManageRole,
  onToggleStatus,
}: UsersTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading users">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <EmptyState
        title="No users found"
        description="Try adjusting your search or filters to find platform users."
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Platform users</caption>
        <thead className="bg-neutral-50 dark:bg-neutral-900/60">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Name
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Email
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Role
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Created Date
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {users.map((user) => {
            const disableReason = getDisableBlockReason(user, currentUserId)
            const statusActionLabel = user.is_active ? 'Disable' : 'Enable'

            return (
              <tr key={user.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
                <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {user.full_name}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {user.email}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {formatUserRoles(user.roles) || getPrimaryRole(user.roles)}
                </td>
                <td className="px-4 py-3">
                  <AdminUserStatusBadge isActive={user.is_active} />
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {formatCreatedAt(user.created_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <Button variant="secondary" size="sm" onClick={() => onView(user)}>
                      View
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => onManageRole(user)}>
                      Role
                    </Button>
                    <Button
                      variant={user.is_active ? 'danger' : 'primary'}
                      size="sm"
                      disabled={Boolean(user.is_active && disableReason)}
                      title={disableReason}
                      onClick={() => onToggleStatus(user)}
                    >
                      {statusActionLabel}
                    </Button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
