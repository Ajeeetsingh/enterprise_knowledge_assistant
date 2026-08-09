import { FilterBar, FilterSearch, FilterSelect } from '@/components/ui/FilterControl'
import type { KnowledgeDomain } from '@/features/knowledge-domains'

export const ALL_DOMAINS_VALUE = ''

export interface DocumentDomainFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  domainId: string
  onDomainChange: (domainId: string) => void
  domains: KnowledgeDomain[]
  domainsLoading?: boolean
}

export default function DocumentDomainFilters({
  search,
  onSearchChange,
  domainId,
  onDomainChange,
  domains,
  domainsLoading = false,
}: DocumentDomainFiltersProps) {
  const options = [
    { value: ALL_DOMAINS_VALUE, label: 'All Domains' },
    ...domains.map((domain) => ({
      value: domain.id,
      label: domain.name,
    })),
  ]

  return (
    <FilterBar aria-label="Document filters">
      <div className="min-w-[220px] flex-1">
        <FilterSearch
          label="Search documents"
          type="search"
          value={search}
          placeholder="Search documents..."
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div className="min-w-[200px] flex-1">
        <FilterSelect
          id="document-domain-filter"
          label="Domain"
          value={domainId}
          disabled={domainsLoading}
          options={options}
          onChange={(event) => onDomainChange(event.target.value)}
        />
      </div>
    </FilterBar>
  )
}
