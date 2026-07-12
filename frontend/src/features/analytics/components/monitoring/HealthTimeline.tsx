import EmptyState from '@/components/ui/EmptyState'
import StatusBadge, { type StatusBadgeTone } from '@/components/ui/StatusBadge'

import type { HealthTimelineItem, ServiceHealthStatus } from '../../types'

export interface HealthTimelineProps {
  items: HealthTimelineItem[]
}

function statusTone(status: ServiceHealthStatus): StatusBadgeTone {
  if (status === 'healthy') return 'good'
  if (status === 'degraded') return 'warn'
  return 'bad'
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
    <div className="data-table-shell">
      <table className="data-table">
        <caption className="sr-only">Operational health timeline</caption>
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">Service</th>
            <th scope="col">Status</th>
            <th scope="col">Detail</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={`${item.timestamp}-${item.event_type}-${item.detail}`}
              className="interactive-row"
            >
              <td className="text-muted">{new Date(item.timestamp).toLocaleString()}</td>
              <td className="font-medium">{item.service}</td>
              <td>
                <StatusBadge tone={statusTone(item.status)} className="capitalize">
                  {item.status}
                </StatusBadge>
              </td>
              <td className="text-muted">{item.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
