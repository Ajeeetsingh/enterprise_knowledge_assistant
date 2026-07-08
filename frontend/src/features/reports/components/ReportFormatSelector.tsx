import Spinner from '@/components/ui/Spinner'

import type { ReportFormat, ReportFormatId } from '../types'

export interface ReportFormatSelectorProps {
  formats: ReportFormat[]
  value: ReportFormatId
  onChange: (format: ReportFormatId) => void
  isLoading?: boolean
}

export default function ReportFormatSelector({
  formats,
  value,
  onChange,
  isLoading = false,
}: ReportFormatSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
        <Spinner size="sm" label="Loading formats" />
        Loading formats…
      </div>
    )
  }

  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-neutral-700 dark:text-neutral-200">Export format</span>
      <select
        className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-950 dark:text-neutral-50"
        value={value}
        onChange={(event) => onChange(event.target.value as ReportFormatId)}
      >
        {formats.map((format) => (
          <option key={format.id} value={format.id}>
            {format.label}
          </option>
        ))}
      </select>
    </label>
  )
}
