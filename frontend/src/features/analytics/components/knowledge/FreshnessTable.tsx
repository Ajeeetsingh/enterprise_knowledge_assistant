import EmptyState from '@/components/ui/EmptyState'

import type { FreshnessItem } from '../../types'

export interface FreshnessTableProps {
  recentUploads: FreshnessItem[]
  longestInactive: FreshnessItem[]
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString()
}

export default function FreshnessTable({
  recentUploads,
  longestInactive,
}: FreshnessTableProps) {
  const rows = [
    ...recentUploads.map((item) => ({ ...item, section: 'Recent upload' as const })),
    ...longestInactive.map((item) => ({ ...item, section: 'Longest inactive' as const })),
  ]

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No freshness data"
        description="No document freshness records are available for the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Content freshness</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Section
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Document
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Collection
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Uploaded
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Updated
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Days Inactive
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {rows.map((item) => (
            <tr key={`${item.section}-${item.document_id}`}>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.section}</td>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.filename}</td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.collection}</td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">
                {formatDate(item.uploaded_at)}
              </td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">
                {formatDate(item.updated_at)}
              </td>
              <td className="px-4 py-3 tabular-nums text-neutral-900 dark:text-neutral-50">
                {item.days_inactive}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
