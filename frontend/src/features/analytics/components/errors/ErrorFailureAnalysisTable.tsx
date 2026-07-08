import EmptyState from '@/components/ui/EmptyState'

import type { ErrorFrequencyItem } from '../../types'

export interface ErrorFailureAnalysisTableProps {
  operations: ErrorFrequencyItem[]
  retrievalFailures: ErrorFrequencyItem[]
}

export default function ErrorFailureAnalysisTable({
  operations,
  retrievalFailures,
}: ErrorFailureAnalysisTableProps) {
  const rows = [
    ...operations.map((item) => ({ ...item, section: 'Failed operation' as const })),
    ...retrievalFailures.map((item) => ({ ...item, section: 'Retrieval failure' as const })),
  ]

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No failure analysis data"
        description="No measurable failure patterns were found for the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Failure analysis</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Section
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Detail
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Category
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {rows.map((item) => (
            <tr key={`${item.section}-${item.label}-${item.category}`}>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.section}</td>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.label}</td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.category}</td>
              <td className="px-4 py-3 tabular-nums text-neutral-900 dark:text-neutral-50">
                {item.count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
