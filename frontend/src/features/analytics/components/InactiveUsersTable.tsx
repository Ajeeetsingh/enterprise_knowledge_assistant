import EmptyState from '@/components/ui/EmptyState'

import type { UserActivityItem } from '../types'

export interface InactiveUsersTableProps {
  users: UserActivityItem[]
}

export default function InactiveUsersTable({ users }: InactiveUsersTableProps) {
  if (users.length === 0) {
    return (
      <EmptyState
        title="No inactive users"
        description="All active accounts recorded activity during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Inactive users</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              User
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {users.map((user) => (
            <tr key={user.user_id}>
              <td className="px-4 py-3">
                <div className="font-medium text-neutral-900 dark:text-neutral-50">
                  {user.full_name}
                </div>
                <div className="text-sm text-neutral-500 dark:text-neutral-400">{user.email}</div>
              </td>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">
                {user.is_active ? 'Active account, no recent activity' : 'Inactive'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
