import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

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
    <DataTable caption="Inactive users">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>User</DataTableHeaderCell>
          <DataTableHeaderCell>Status</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {users.map((user) => (
          <DataTableRow key={user.user_id}>
            <DataTableCell>
              <div className="font-medium">{user.full_name}</div>
              <div className="text-sm text-muted">{user.email}</div>
            </DataTableCell>
            <DataTableCell>
              {user.is_active ? 'Active account, no recent activity' : 'Inactive'}
            </DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
