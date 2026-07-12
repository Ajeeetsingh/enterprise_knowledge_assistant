import { type ReactNode } from 'react'

import MetricIcon, { type MetricIconName } from '@/components/ui/MetricIcon'
import { cn } from '@/utils/cn'

import { formatMetricValue, formatPercentValue } from '../types'

export type MetricTone = 'neutral' | 'good' | 'warn' | 'bad'
export type MetricSize = 'primary' | 'secondary'

export interface AnalyticsKPICardProps {
  label: string
  value: number | string | null
  format?: 'number' | 'percent' | 'decimal' | 'text'
  icon?: MetricIconName
  tone?: MetricTone
  size?: MetricSize
  className?: string
  hint?: ReactNode
}

function formatValue(
  value: number | string | null,
  format: AnalyticsKPICardProps['format'],
): string {
  if (value === null || value === 'N/A') {
    return 'N/A'
  }
  if (typeof value === 'string') {
    return value
  }
  if (format === 'percent') {
    return formatPercentValue(value)
  }
  if (format === 'decimal') {
    return formatMetricValue(value)
  }
  if (format === 'text') {
    return String(value)
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)
}

function inferTone(label: string, format: AnalyticsKPICardProps['format']): MetricTone | undefined {
  const lower = label.toLowerCase()
  if (
    lower.includes('error') ||
    lower.includes('failure') ||
    lower.includes('stale') ||
    lower.includes('unused')
  ) {
    return 'bad'
  }
  if (lower.includes('success') || lower.includes('healthy') || lower.includes('ready')) {
    return 'good'
  }
  if (lower.includes('degraded') || lower.includes('warning')) {
    return 'warn'
  }
  if (format === 'percent' && !lower.includes('rate')) {
    return undefined
  }
  return undefined
}

function toneForPercent(label: string, value: number): MetricTone {
  const lower = label.toLowerCase()
  if (lower.includes('error') || lower.includes('failure')) {
    if (value >= 10) return 'bad'
    if (value >= 3) return 'warn'
    return 'good'
  }
  if (lower.includes('success') || lower.includes('free') || lower.includes('citation')) {
    if (value >= 90) return 'good'
    if (value >= 70) return 'warn'
    return 'bad'
  }
  return 'neutral'
}

export default function AnalyticsKPICard({
  label,
  value,
  format = 'number',
  icon,
  tone,
  size = 'primary',
  className,
  hint,
}: AnalyticsKPICardProps) {
  const formatted = formatValue(value, format)
  const isNa = formatted === 'N/A'

  let resolvedTone = tone ?? inferTone(label, format)
  if (!resolvedTone && format === 'percent' && typeof value === 'number') {
    resolvedTone = toneForPercent(label, value)
  }

  const valueClass = cn(
    'metric-card__value',
    size === 'primary' ? 'metric-card__value--primary' : 'metric-card__value--secondary',
    isNa && 'metric-card__value--na',
    !isNa && resolvedTone === 'good' && 'metric-card__value--good',
    !isNa && resolvedTone === 'warn' && 'metric-card__value--warn',
    !isNa && resolvedTone === 'bad' && 'metric-card__value--bad',
  )

  const iconTone =
    resolvedTone === 'good'
      ? 'good'
      : resolvedTone === 'warn'
        ? 'warn'
        : resolvedTone === 'bad'
          ? 'bad'
          : 'default'

  return (
    <div className={cn('metric-card', className)}>
      <p className="metric-card__label">
        {icon && <MetricIcon name={icon} tone={iconTone} />}
        <span>{label}</span>
      </p>
      <p className={valueClass} aria-label={`${label}: ${formatted}`}>
        {formatted}
      </p>
      {hint ? <div className="mt-2 text-xs text-muted">{hint}</div> : null}
    </div>
  )
}
