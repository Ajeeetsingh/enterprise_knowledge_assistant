import EmptyState from '@/components/ui/EmptyState'
import StatusBadge, { type StatusBadgeTone } from '@/components/ui/StatusBadge'

import type { ServiceHealthStatus, ServiceStatusItem } from '../../types'

export interface ServiceStatusTableProps {
  items: ServiceStatusItem[]
}

function statusTone(status: ServiceHealthStatus): StatusBadgeTone {
  if (status === 'healthy') return 'good'
  if (status === 'degraded') return 'warn'
  return 'bad'
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
    <div className="data-table-shell">
      <table className="data-table">
        <caption className="sr-only">Platform service status</caption>
        <thead>
          <tr>
            <th scope="col">Service</th>
            <th scope="col">Status</th>
            <th scope="col">Detail</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.service} className="interactive-row">
              <td className="font-medium">{SERVICE_LABELS[item.service] ?? item.service}</td>
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
