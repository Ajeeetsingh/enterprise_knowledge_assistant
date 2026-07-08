import Spinner from '@/components/ui/Spinner'

import type { ReportModule, ReportModuleId } from '../types'

export interface ModuleSelectorProps {
  modules: ReportModule[]
  value: ReportModuleId
  onChange: (module: ReportModuleId) => void
  isLoading?: boolean
}

export default function ModuleSelector({
  modules,
  value,
  onChange,
  isLoading = false,
}: ModuleSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
        <Spinner size="sm" label="Loading modules" />
        Loading modules…
      </div>
    )
  }

  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-neutral-700 dark:text-neutral-200">Analytics module</span>
      <select
        className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-950 dark:text-neutral-50"
        value={value}
        onChange={(event) => onChange(event.target.value as ReportModuleId)}
      >
        {modules.map((module) => (
          <option key={module.id} value={module.id}>
            {module.title}
          </option>
        ))}
      </select>
    </label>
  )
}
