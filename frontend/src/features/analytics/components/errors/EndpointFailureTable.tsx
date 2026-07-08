import EmptyState from '@/components/ui/EmptyState'

import type { EndpointFailureItem } from '../../types'

export interface EndpointFailureTableProps {
  items: EndpointFailureItem[]
}

export default function EndpointFailureTable({ items }: EndpointFailureTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No endpoint failures recorded"
        description="No endpoint or resource failures were captured during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Endpoint failure analysis</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Endpoint
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Service
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Count
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={`${item.service}-${item.endpoint}`}>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.endpoint}</td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.service}</td>
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
