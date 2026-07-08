import EmptyState from '@/components/ui/EmptyState'

import type { DocumentUsageItem } from '../../types'

export interface TopDocumentsTableProps {
  items: DocumentUsageItem[]
}

export default function TopDocumentsTable({ items }: TopDocumentsTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No document usage recorded"
        description="No documents were cited during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Top documents by citation usage</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Document
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Collection
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Views
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Citations
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={item.document_id}>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.filename}</td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.collection}</td>
              <td className="px-4 py-3 tabular-nums text-neutral-900 dark:text-neutral-50">
                {item.view_count}
              </td>
              <td className="px-4 py-3 tabular-nums text-neutral-900 dark:text-neutral-50">
                {item.citation_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
