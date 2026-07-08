import EmptyState from '@/components/ui/EmptyState'

import type { KnowledgeGapItem } from '../../types'

const CATEGORY_LABELS: Record<string, string> = {
  questions_without_documents: 'No documents retrieved',
  failed_search: 'Failed search',
  never_cited_document: 'Never cited',
  never_searched_document: 'Never searched',
  low_engagement_collection: 'Low engagement collection',
}

export interface KnowledgeGapTableProps {
  items: KnowledgeGapItem[]
}

export default function KnowledgeGapTable({ items }: KnowledgeGapTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No knowledge gaps detected"
        description="No measurable knowledge gaps were found for the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Knowledge gap analysis</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Category
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Detail
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={`${item.category}-${item.label}`}>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">
                {CATEGORY_LABELS[item.category] ?? item.category}
              </td>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.label}</td>
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
