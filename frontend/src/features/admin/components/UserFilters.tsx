import Input from '@/components/ui/Input'
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

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string
  label: string
  value: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-50 dark:focus:ring-offset-neutral-900"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function UserFilters({
  filters,
  onChange,
  search,
  onSearchChange,
}: UserFiltersProps) {
  return (
    <section
      aria-label="User filters"
      className="grid gap-4 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900 sm:grid-cols-2 lg:grid-cols-4"
    >
      <Input
        label="Search users"
        type="search"
        value={search}
        placeholder="Search by name or email"
        onChange={(event) => onSearchChange(event.target.value)}
      />

      <SelectField
        id="admin-user-role-filter"
        label="Role"
        value={filters.role}
        options={ROLE_OPTIONS}
        onChange={(value) => onChange({ ...filters, role: value as AdminRoleFilter })}
      />

      <SelectField
        id="admin-user-status-filter"
        label="Status"
        value={filters.status}
        options={STATUS_OPTIONS}
        onChange={(value) => onChange({ ...filters, status: value as AdminStatusFilter })}
      />
    </section>
  )
}
