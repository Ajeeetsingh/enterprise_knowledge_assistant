import type { MonitoringSummary } from '../types'
import SummaryMetricCard from './SummaryMetricCard'

const SUMMARY_METRICS: Array<{
  key: keyof MonitoringSummary
  label: string
}> = [
  { key: 'total_users', label: 'Total Users' },
  { key: 'active_users', label: 'Active Users' },
  { key: 'total_documents', label: 'Total Documents' },
  { key: 'total_conversations', label: 'Total Conversations' },
  { key: 'questions_today', label: 'Questions Today' },
  { key: 'failed_logins_today', label: 'Failed Logins Today' },
  { key: 'audit_events_today', label: 'Audit Events Today' },
]

export interface SummaryMetricsGridProps {
  summary: MonitoringSummary
}

export default function SummaryMetricsGrid({ summary }: SummaryMetricsGridProps) {
  return (
    <section aria-labelledby="monitoring-summary-heading">
      <h2 id="monitoring-summary-heading" className="sr-only">
        Summary metrics
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {SUMMARY_METRICS.map(({ key, label }) => (
          <SummaryMetricCard key={key} label={label} value={summary[key]} />
        ))}
      </div>
    </section>
  )
}
