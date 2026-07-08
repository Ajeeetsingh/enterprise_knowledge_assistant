import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'

import { formatUptime, type SystemMetrics } from '../types'

export interface SystemMetricsPanelProps {
  metrics: SystemMetrics
}

export default function SystemMetricsPanel({ metrics }: SystemMetricsPanelProps) {
  return (
    <section aria-labelledby="system-metrics-heading">
      <Card title="System status">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
              Database
            </dt>
            <dd className="mt-2">
              <Badge
                variant={metrics.database_connected ? 'success' : 'error'}
                aria-label={
                  metrics.database_connected
                    ? 'Database connected'
                    : 'Database disconnected'
                }
              >
                {metrics.database_connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
              Uptime
            </dt>
            <dd
              className="mt-2 text-lg font-semibold tabular-nums text-neutral-900 dark:text-neutral-50"
              aria-label={`Uptime: ${formatUptime(metrics.uptime_seconds)}`}
            >
              {formatUptime(metrics.uptime_seconds)}
            </dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
              Application Version
            </dt>
            <dd className="mt-2 text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              {metrics.version}
            </dd>
          </div>
        </dl>
      </Card>
    </section>
  )
}
