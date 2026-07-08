import Input from '@/components/ui/Input'

import type { AdminStatusFilter, AdminVisibilityFilter, DocumentFilterState } from '../utils/documentFilters'

export interface DocumentFiltersProps {
  filters: DocumentFilterState
  onChange: (filters: DocumentFilterState) => void
  search: string
  onSearchChange: (value: string) => void
}

const STATUS_OPTIONS: Array<{ value: AdminStatusFilter; label: string }> = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'READY', label: 'Ready' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'FAILED', label: 'Failed' },
]

const VISIBILITY_OPTIONS: Array<{ value: AdminVisibilityFilter; label: string }> = [
  { value: 'ALL', label: 'All visibility' },
  { value: 'PUBLIC', label: 'Public' },
  { value: 'PRIVATE', label: 'Private' },
  { value: 'ROLE_BASED', label: 'Role-based' },
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

export default function DocumentFilters({
  filters,
  onChange,
  search,
  onSearchChange,
}: DocumentFiltersProps) {
  return (
    <section
      aria-label="Document filters"
      className="grid gap-4 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900 sm:grid-cols-2 lg:grid-cols-4"
    >
      <Input
        label="Search documents"
        type="search"
        value={search}
        placeholder="Search by document name"
        onChange={(event) => onSearchChange(event.target.value)}
      />

      <SelectField
        id="admin-document-status-filter"
        label="Status"
        value={filters.status}
        options={STATUS_OPTIONS}
        onChange={(value) =>
          onChange({ ...filters, status: value as AdminStatusFilter })
        }
      />

      <SelectField
        id="admin-document-visibility-filter"
        label="Visibility"
        value={filters.visibility}
        options={VISIBILITY_OPTIONS}
        onChange={(value) =>
          onChange({ ...filters, visibility: value as AdminVisibilityFilter })
        }
      />
    </section>
  )
}
