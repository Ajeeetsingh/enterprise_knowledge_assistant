import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { UserActivityItem } from '../types'

export interface TopUsersTableProps {
  users: UserActivityItem[]
}

export default function TopUsersTable({ users }: TopUsersTableProps) {
  if (users.length === 0) {
    return (
      <EmptyState
        title="No active users"
        description="No user activity was recorded for the selected period."
      />
    )
  }

  return (
    <DataTable caption="Top active users">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>User</DataTableHeaderCell>
          <DataTableHeaderCell>Questions</DataTableHeaderCell>
          <DataTableHeaderCell>Conversations</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {users.map((user) => (
          <DataTableRow key={user.user_id}>
            <DataTableCell>
              <div className="font-medium">{user.full_name}</div>
              <div className="text-sm text-muted">{user.email}</div>
            </DataTableCell>
            <DataTableCell className="tabular-nums">{user.question_count}</DataTableCell>
            <DataTableCell className="tabular-nums">{user.conversation_count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
