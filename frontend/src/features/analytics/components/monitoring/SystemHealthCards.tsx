import StatusBadge, { type StatusBadgeTone } from '@/components/ui/StatusBadge'

import AnalyticsKPICard from '../AnalyticsKPICard'
import type { ServiceHealthStatus, SystemMonitoringOverview } from '../../types'
import { formatUptime } from '../../types'

export interface SystemHealthCardsProps {
  overview: SystemMonitoringOverview
}

function statusTone(status: ServiceHealthStatus): StatusBadgeTone {
  if (status === 'healthy') return 'good'
  if (status === 'degraded') return 'warn'
  return 'bad'
}

function HealthCard({ label, status }: { label: string; status: ServiceHealthStatus }) {
  return (
    <div className="metric-card">
      <p className="metric-card__label">
        <span>{label}</span>
      </p>
      <div className="mt-3">
        <StatusBadge tone={statusTone(status)} className="capitalize">
          {status}
        </StatusBadge>
      </div>
    </div>
  )
}

export default function SystemHealthCards({ overview }: SystemHealthCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <HealthCard label="API Health" status={overview.api_health} />
      <HealthCard label="Database Health" status={overview.database_health} />
      <HealthCard label="Search Service" status={overview.search_service_health} />
      <HealthCard label="Vector Index" status={overview.vector_index_health} />
      <div className="metric-card sm:col-span-2 xl:col-span-2">
        <p className="metric-card__label">
          <span>Overall System Status</span>
        </p>
        <div className="mt-3">
          <StatusBadge tone={statusTone(overview.overall_system_status)} className="capitalize">
            {overview.overall_system_status}
          </StatusBadge>
        </div>
      </div>
      <AnalyticsKPICard
        label="Uptime"
        value={formatUptime(overview.uptime_seconds)}
        format="text"
        icon="monitoring"
        size="primary"
        tone="good"
      />
      <AnalyticsKPICard
        label="Version"
        value={overview.version}
        format="text"
        icon="monitoring"
        size="secondary"
      />
    </div>
  )
}
