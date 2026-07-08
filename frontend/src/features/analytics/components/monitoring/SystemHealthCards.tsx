import Card from '@/components/ui/Card'
import clsx from 'clsx'

import type { ServiceHealthStatus, SystemMonitoringOverview } from '../../types'
import { formatUptime } from '../../types'

export interface SystemHealthCardsProps {
  overview: SystemMonitoringOverview
}

const STATUS_STYLES: Record<ServiceHealthStatus, string> = {
  healthy:
    'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300',
  degraded:
    'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  unavailable:
    'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
}

function HealthCard({ label, status }: { label: string; status: ServiceHealthStatus }) {
  return (
    <Card>
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</p>
      <p
        className={clsx(
          'mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold capitalize',
          STATUS_STYLES[status],
        )}
      >
        {status}
      </p>
    </Card>
  )
}

export default function SystemHealthCards({ overview }: SystemHealthCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <HealthCard label="API Health" status={overview.api_health} />
      <HealthCard label="Database Health" status={overview.database_health} />
      <HealthCard label="Search Service" status={overview.search_service_health} />
      <HealthCard label="Vector Index" status={overview.vector_index_health} />
      <Card className="sm:col-span-2 xl:col-span-2">
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Overall System Status
        </p>
        <p
          className={clsx(
            'mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold capitalize',
            STATUS_STYLES[overview.overall_system_status],
          )}
        >
          {overview.overall_system_status}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Uptime</p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatUptime(overview.uptime_seconds)}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Version</p>
        <p className="mt-2 text-3xl font-bold text-neutral-900 dark:text-neutral-50">
          {overview.version}
        </p>
      </Card>
    </div>
  )
}
