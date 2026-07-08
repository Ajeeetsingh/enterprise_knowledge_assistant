import Card from '@/components/ui/Card'

import { formatMetricValue, formatPercentValue } from '../types'

export interface AnalyticsKPICardProps {
  label: string
  value: number
  format?: 'number' | 'percent' | 'decimal'
}

function formatValue(value: number, format: AnalyticsKPICardProps['format']): string {
  if (format === 'percent') {
    return formatPercentValue(value)
  }
  if (format === 'decimal') {
    return formatMetricValue(value)
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)
}

export default function AnalyticsKPICard({
  label,
  value,
  format = 'number',
}: AnalyticsKPICardProps) {
  const formatted = formatValue(value, format)

  return (
    <Card>
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</p>
      <p
        className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50"
        aria-label={`${label}: ${formatted}`}
      >
        {formatted}
      </p>
    </Card>
  )
}
