import EmptyState from '@/components/ui/EmptyState'

import type { QuestionFrequencyItem } from '../../types'

export interface TopQuestionsTableProps {
  items: QuestionFrequencyItem[]
}

export default function TopQuestionsTable({ items }: TopQuestionsTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No questions recorded"
        description="No user questions were captured during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Top user questions</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Question
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={item.question}>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.question}</td>
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
