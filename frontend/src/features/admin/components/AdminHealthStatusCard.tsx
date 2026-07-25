import MetricIcon, { type MetricIconName } from '@/components/ui/MetricIcon'
import type { ServiceHealthStatus } from '@/features/analytics/types'
import { cn } from '@/utils/cn'

export interface AdminHealthStatusCardProps {
  label: string
  icon: MetricIconName
  /** Live status from monitoring API, or null when unavailable. */
  status: ServiceHealthStatus | null
  isLoading?: boolean
}

function statusTone(
  status: ServiceHealthStatus | null,
): 'good' | 'warn' | 'bad' | 'default' {
  if (status === 'healthy') return 'good'
  if (status === 'degraded') return 'warn'
  if (status === 'unavailable') return 'bad'
  return 'default'
}

function statusDotClass(status: ServiceHealthStatus | null): string {
  if (status === 'healthy') return 'bg-status-good'
  if (status === 'degraded') return 'bg-status-warn'
  if (status === 'unavailable') return 'bg-status-bad'
  return 'bg-muted'
}

function formatStatusLabel(status: ServiceHealthStatus | null): string {
  if (!status) return 'Unavailable'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export default function AdminHealthStatusCard({
  label,
  icon,
  status,
  isLoading = false,
}: AdminHealthStatusCardProps) {
  const tone = statusTone(status)
  const display = formatStatusLabel(status)

  if (isLoading) {
    return (
      <div
        className={cn(
          'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
          'px-4 py-3 shadow-elevation-sm',
        )}
        role="status"
        aria-label={`${label}: Loading`}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="h-4 w-20 animate-pulse rounded bg-overlay" />
          <div className="h-4 w-16 animate-pulse rounded bg-overlay" />
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
        'px-4 py-3 shadow-elevation-sm',
      )}
      aria-label={`${label}: ${display}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <MetricIcon name={icon} tone={tone === 'default' ? 'default' : tone} />
          <span className="truncate text-sm font-medium text-foreground">{label}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <span
            className={cn('size-2 rounded-full', statusDotClass(status))}
            aria-hidden
          />
          <span
            className={cn(
              'text-sm font-medium capitalize',
              status === 'healthy' && 'text-status-good',
              status === 'degraded' && 'text-status-warn',
              status === 'unavailable' && 'text-status-bad',
              !status && 'text-muted',
            )}
          >
            {display}
          </span>
        </div>
      </div>
    </div>
  )
}
