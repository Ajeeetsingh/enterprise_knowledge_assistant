import Input from '@/components/ui/Input'
import { DATE_RANGE_PRESET_OPTIONS } from '@/features/analytics/constants'
import type { AnalyticsFilterParams, DateRangePreset } from '@/features/analytics/types'

export interface DateRangeSelectorProps {
  filters: AnalyticsFilterParams
  onChange: (filters: AnalyticsFilterParams) => void
}

export default function DateRangeSelector({ filters, onChange }: DateRangeSelectorProps) {
  const preset = filters.range_preset ?? 'last_7_days'
  const isCustom = preset === 'custom'

  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-neutral-700 dark:text-neutral-200">Date range</span>
        <select
          className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-950 dark:text-neutral-50"
          value={preset}
          onChange={(event) =>
            onChange({
              ...filters,
              range_preset: event.target.value as DateRangePreset,
            })
          }
        >
          {DATE_RANGE_PRESET_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      {isCustom ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-neutral-700 dark:text-neutral-200">Start date</span>
            <Input
              type="date"
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
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-neutral-700 dark:text-neutral-200">End date</span>
            <Input
              type="date"
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
          </label>
        </div>
      ) : null}
    </div>
  )
}
