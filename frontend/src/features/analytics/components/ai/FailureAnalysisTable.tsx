import EmptyState from '@/components/ui/EmptyState'

import type { FailureAnalysisItem } from '../../types'

export interface FailureAnalysisTableProps {
  items: FailureAnalysisItem[]
}

export default function FailureAnalysisTable({ items }: FailureAnalysisTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No failures recorded"
        description="No retrieval failures occurred during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Failed retrieval analysis</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Reason
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={item.reason}>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.reason}</td>
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
