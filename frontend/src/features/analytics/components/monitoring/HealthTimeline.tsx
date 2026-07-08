import EmptyState from '@/components/ui/EmptyState'
import clsx from 'clsx'

import type { HealthTimelineItem, ServiceHealthStatus } from '../../types'

export interface HealthTimelineProps {
  items: HealthTimelineItem[]
}

const STATUS_STYLES: Record<ServiceHealthStatus, string> = {
  healthy: 'text-green-700 dark:text-green-300',
  degraded: 'text-amber-700 dark:text-amber-300',
  unavailable: 'text-red-700 dark:text-red-300',
}

export default function HealthTimeline({ items }: HealthTimelineProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No health events recorded"
        description="No operational health events were captured during the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Operational health timeline</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
            <th scope="col" className="px-4 py-3 font-medium">
              Time
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Service
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Status
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Detail
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {items.map((item) => (
            <tr key={`${item.timestamp}-${item.event_type}-${item.detail}`}>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">
                {new Date(item.timestamp).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">{item.service}</td>
              <td
                className={clsx(
                  'px-4 py-3 font-medium capitalize',
                  STATUS_STYLES[item.status],
                )}
              >
                {item.status}
              </td>
              <td className="px-4 py-3 text-neutral-700 dark:text-neutral-300">{item.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
