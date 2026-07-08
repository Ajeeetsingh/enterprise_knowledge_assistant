import EmptyState from '@/components/ui/EmptyState'
import clsx from 'clsx'

import type { ServiceHealthStatus, ServiceStatusItem } from '../../types'

export interface ServiceStatusTableProps {
  items: ServiceStatusItem[]
}

const STATUS_STYLES: Record<ServiceHealthStatus, string> = {
  healthy: 'text-green-700 dark:text-green-300',
  degraded: 'text-amber-700 dark:text-amber-300',
  unavailable: 'text-red-700 dark:text-red-300',
}

const SERVICE_LABELS: Record<string, string> = {
  authentication: 'Authentication Service',
  database: 'Database',
  ai_service: 'AI Service',
  retrieval_service: 'Retrieval Service',
  background_workers: 'Background Workers',
}

export default function ServiceStatusTable({ items }: ServiceStatusTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No service status data"
        description="Service health probes are unavailable for the selected period."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
        <caption className="sr-only">Platform service status</caption>
        <thead>
          <tr className="text-left text-sm text-neutral-500 dark:text-neutral-400">
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
            <tr key={item.service}>
              <td className="px-4 py-3 text-neutral-900 dark:text-neutral-50">
                {SERVICE_LABELS[item.service] ?? item.service}
              </td>
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
