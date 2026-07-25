import MetricIcon, { type MetricIconName } from '@/components/ui/MetricIcon'
import { cn } from '@/utils/cn'

export interface AdminMetricCardProps {
  label: string
  value: string
  icon?: MetricIconName
  tone?: 'neutral' | 'good' | 'warn' | 'bad'
  size?: 'primary' | 'secondary'
  /** When true, shows a skeleton pulse instead of the value. */
  isLoading?: boolean
}

export default function AdminMetricCard({
  label,
  value,
  icon,
  tone = 'neutral',
  size = 'primary',
  isLoading = false,
}: AdminMetricCardProps) {
  const isUnavailable = !isLoading && (value === 'N/A' || value === 'Unavailable')

  const valueClass = cn(
    'metric-card__value',
    size === 'primary' ? 'metric-card__value--primary' : 'metric-card__value--secondary',
    isUnavailable && 'metric-card__value--na',
    !isUnavailable && tone === 'good' && 'metric-card__value--good',
    !isUnavailable && tone === 'warn' && 'metric-card__value--warn',
    !isUnavailable && tone === 'bad' && 'metric-card__value--bad',
  )

  const iconTone =
    tone === 'good' ? 'good' : tone === 'warn' ? 'warn' : tone === 'bad' ? 'bad' : 'default'

  const displayValue = isLoading ? '' : value
  const ariaValue = isLoading ? 'Loading' : value

  return (
    <div className="metric-card">
      <p className="metric-card__label">
        {icon && <MetricIcon name={icon} tone={iconTone} />}
        <span>{label}</span>
      </p>
      {isLoading ? (
        <div
          className="mt-3 h-8 w-24 animate-pulse rounded-md bg-overlay"
          role="status"
          aria-label={`${label}: Loading`}
        />
      ) : (
        <p className={valueClass} aria-label={`${label}: ${ariaValue}`}>
          {displayValue}
        </p>
      )}
    </div>
  )
}
