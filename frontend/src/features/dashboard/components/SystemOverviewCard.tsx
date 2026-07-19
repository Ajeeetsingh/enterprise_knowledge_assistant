import { Link } from 'react-router-dom'

import Skeleton from '@/components/ui/Skeleton'
import StatusBadge from '@/components/ui/StatusBadge'
import { useMonitoringSummary, useSystemMetrics } from '@/features/monitoring/hooks'
import { cn } from '@/utils/cn'

/** Admin-only compact system snapshot (max 4 metrics). */
export default function SystemOverviewCard() {
  const summaryQuery = useMonitoringSummary()
  const metricsQuery = useSystemMetrics()

  const isLoading = summaryQuery.isLoading || metricsQuery.isLoading
  const summary = summaryQuery.data
  const dbConnected = metricsQuery.data?.database_connected

  return (
    <section
      className={cn(
        'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
        'p-5 shadow-elevation-sm',
      )}
      aria-labelledby="dashboard-system-heading"
    >
      <div className="flex items-start justify-between gap-3">
        <h2
          id="dashboard-system-heading"
          className="text-sm font-semibold tracking-tight text-foreground"
        >
          System overview
        </h2>
        <Link
          to="/admin/analytics"
          className={cn(
            'shrink-0 text-xs font-medium text-accent transition-colors hover:text-accent-hover',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          View full analytics →
        </Link>
      </div>

      {isLoading || !summary ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-busy="true">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-3 w-20" variant="text" />
              <Skeleton className="h-6 w-10" />
            </div>
          ))}
        </div>
      ) : (
        <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs text-muted">Active users</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">
              {summary.active_users}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Total documents</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">
              {summary.total_documents}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Questions today</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">
              {summary.questions_today}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">System status</dt>
            <dd className="mt-1.5">
              <StatusBadge tone={dbConnected === false ? 'bad' : 'good'}>
                {dbConnected === false ? 'Degraded' : 'Healthy'}
              </StatusBadge>
            </dd>
          </div>
        </dl>
      )}
    </section>
  )
}
