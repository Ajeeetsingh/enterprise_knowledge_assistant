import Button from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'

import { formatCreatedAt, formatUserRoles, type User } from '../types'
import UserStatusBadge from './UserStatusBadge'

export interface UserTableProps {
  users: User[]
  isLoading: boolean
  onDisable: (user: User) => void
}

export default function UserTable({ users, isLoading, onDisable }: UserTableProps) {
  const { user: currentUser } = useAuth()

  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading users">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Enterprise users</caption>
        <thead className="bg-neutral-50 dark:bg-neutral-900/60">
          <tr>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Name
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Email
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Role
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Created At
            </th>
            <th
              scope="col"
              className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {users.map((user) => {
            const isSelf = currentUser?.id === user.id
            const canDisable = user.is_active && !isSelf

            return (
              <tr key={user.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
                <td className="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {user.full_name}
                  {user.is_superuser && (
                    <span className="ml-2 text-xs font-normal text-neutral-500 dark:text-neutral-400">
                      (Superuser)
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {user.email}
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {formatUserRoles(user.roles)}
                </td>
                <td className="px-4 py-3">
                  <UserStatusBadge isActive={user.is_active} />
                </td>
                <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {formatCreatedAt(user.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!canDisable}
                    title={
                      isSelf
                        ? 'You cannot disable your own account.'
                        : !user.is_active
                          ? 'User is already inactive.'
                          : undefined
                    }
                    onClick={() => onDisable(user)}
                  >
                    Disable
                  </Button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
