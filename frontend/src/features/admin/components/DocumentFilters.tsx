import { FilterBar, FilterSearch, FilterSelect } from '@/components/ui/FilterControl'

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

export default function DocumentFilters({
  filters,
  onChange,
  search,
  onSearchChange,
}: DocumentFiltersProps) {
  return (
    <FilterBar aria-label="Document filters">
      <div className="min-w-[220px] flex-1">
        <FilterSearch
          label="Search documents"
          type="search"
          value={search}
          placeholder="Search by document name"
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div className="min-w-[180px] flex-1">
        <FilterSelect
          id="admin-document-status-filter"
          label="Status"
          value={filters.status}
          options={STATUS_OPTIONS}
          onChange={(event) =>
            onChange({ ...filters, status: event.target.value as AdminStatusFilter })
          }
        />
      </div>

      <div className="min-w-[180px] flex-1">
        <FilterSelect
          id="admin-document-visibility-filter"
          label="Visibility"
          value={filters.visibility}
          options={VISIBILITY_OPTIONS}
          onChange={(event) =>
            onChange({ ...filters, visibility: event.target.value as AdminVisibilityFilter })
          }
        />
      </div>
    </FilterBar>
  )
}
