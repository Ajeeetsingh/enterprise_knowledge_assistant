import { FilterBar, FilterSearch, FilterSelect } from '@/components/ui/FilterControl'
import { Role } from '@/types/permissions'

import type { AdminRoleFilter, AdminStatusFilter, UserFilterState } from '../utils/userFilters'

export interface UserFiltersProps {
  filters: UserFilterState
  onChange: (filters: UserFilterState) => void
  search: string
  onSearchChange: (value: string) => void
}

const ROLE_OPTIONS: Array<{ value: AdminRoleFilter; label: string }> = [
  { value: 'ALL', label: 'All roles' },
  { value: Role.Admin, label: 'Admin' },
  { value: Role.HR, label: 'HR' },
  { value: Role.Finance, label: 'Finance' },
  { value: Role.Employee, label: 'Employee' },
]

const STATUS_OPTIONS: Array<{ value: AdminStatusFilter; label: string }> = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'DISABLED', label: 'Disabled' },
]

export default function UserFilters({
  filters,
  onChange,
  search,
  onSearchChange,
}: UserFiltersProps) {
  return (
    <FilterBar aria-label="User filters">
      <div className="min-w-[220px] flex-1">
        <FilterSearch
          label="Search users"
          type="search"
          value={search}
          placeholder="Search by name or email"
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div className="min-w-[180px] flex-1">
        <FilterSelect
          id="admin-user-role-filter"
          label="Role"
          value={filters.role}
          options={ROLE_OPTIONS}
          onChange={(event) =>
            onChange({ ...filters, role: event.target.value as AdminRoleFilter })
          }
        />
      </div>

      <div className="min-w-[180px] flex-1">
        <FilterSelect
          id="admin-user-status-filter"
          label="Status"
          value={filters.status}
          options={STATUS_OPTIONS}
          onChange={(event) =>
            onChange({ ...filters, status: event.target.value as AdminStatusFilter })
          }
        />
      </div>
    </FilterBar>
  )
}
