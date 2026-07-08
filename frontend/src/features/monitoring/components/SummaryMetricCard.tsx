import Card from '@/components/ui/Card'

import { formatMetricValue } from '../types'

export interface SummaryMetricCardProps {
  label: string
  value: number
}

export default function SummaryMetricCard({ label, value }: SummaryMetricCardProps) {
  return (
    <Card>
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</p>
      <p
        className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50"
        aria-label={`${label}: ${formatMetricValue(value)}`}
      >
        {formatMetricValue(value)}
      </p>
    </Card>
  )
}
