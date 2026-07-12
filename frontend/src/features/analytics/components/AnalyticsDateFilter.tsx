import { FilterBar, FilterLabel, FilterSelect } from '@/components/ui/FilterControl'
import Input from '@/components/ui/Input'

import { DATE_RANGE_PRESET_OPTIONS } from '../constants'
import type { AnalyticsFilterParams, DateRangePreset } from '../types'

export interface AnalyticsDateFilterProps {
  filters: AnalyticsFilterParams
  onChange: (filters: AnalyticsFilterParams) => void
}

export default function AnalyticsDateFilter({ filters, onChange }: AnalyticsDateFilterProps) {
  const preset = filters.range_preset ?? 'last_7_days'
  const isCustom = preset === 'custom'

  return (
    <FilterBar aria-label="Date range filter">
      <div className="min-w-[200px]">
        <FilterSelect
          id="analytics-date-range"
          label="Date range"
          value={preset}
          options={DATE_RANGE_PRESET_OPTIONS}
          onChange={(event) =>
            onChange({
              ...filters,
              range_preset: event.target.value as DateRangePreset,
            })
          }
        />
      </div>

      {isCustom ? (
        <>
          <div className="min-w-[180px]">
            <FilterLabel htmlFor="analytics-start-date">Start date</FilterLabel>
            <Input
              id="analytics-start-date"
              type="date"
              className="filter-control"
              value={filters.start_date?.slice(0, 10) ?? ''}
              onChange={(event) => {
                const nextFilters = { ...filters }
                if (event.target.value) {
                  nextFilters.start_date = `${event.target.value}T00:00:00Z`
                } else {
                  delete nextFilters.start_date
                }
                onChange(nextFilters)
              }}
            />
          </div>
          <div className="min-w-[180px]">
            <FilterLabel htmlFor="analytics-end-date">End date</FilterLabel>
            <Input
              id="analytics-end-date"
              type="date"
              className="filter-control"
              value={filters.end_date?.slice(0, 10) ?? ''}
              onChange={(event) => {
                const nextFilters = { ...filters }
                if (event.target.value) {
                  nextFilters.end_date = `${event.target.value}T23:59:59Z`
                } else {
                  delete nextFilters.end_date
                }
                onChange(nextFilters)
              }}
            />
          </div>
        </>
      ) : null}
    </FilterBar>
  )
}
