import ActionButton from '@/components/ui/ActionButton'
import EmptyState from '@/components/ui/EmptyState'
import StatusBadge from '@/components/ui/StatusBadge'
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
    return <StatusBadge tone="good">Active</StatusBadge>
  }

  return <StatusBadge tone="bad">Disabled</StatusBadge>
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
            className="h-12 animate-pulse rounded-md bg-overlay"
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
    <div className="data-table-shell">
      <table className="data-table">
        <caption className="sr-only">Platform users</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th scope="col">Created Date</th>
            <th scope="col" className="text-right">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const disableReason = getDisableBlockReason(user, currentUserId)
            const statusActionLabel = user.is_active ? 'Disable' : 'Enable'

            return (
              <tr key={user.id} className="interactive-row">
                <td className="font-medium">{user.full_name}</td>
                <td className="text-muted">{user.email}</td>
                <td className="text-muted">
                  {formatUserRoles(user.roles) || getPrimaryRole(user.roles)}
                </td>
                <td>
                  <AdminUserStatusBadge isActive={user.is_active} />
                </td>
                <td className="text-muted">{formatCreatedAt(user.created_at)}</td>
                <td>
                  <div className="flex justify-end gap-2">
                    <ActionButton onClick={() => onView(user)}>View</ActionButton>
                    <ActionButton onClick={() => onManageRole(user)}>Role</ActionButton>
                    <ActionButton
                      destructive={user.is_active}
                      disabled={Boolean(user.is_active && disableReason)}
                      title={disableReason}
                      onClick={() => onToggleStatus(user)}
                    >
                      {statusActionLabel}
                    </ActionButton>
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
