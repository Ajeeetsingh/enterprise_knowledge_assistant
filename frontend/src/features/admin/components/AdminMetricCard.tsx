import MetricIcon, { type MetricIconName } from '@/components/ui/MetricIcon'
import { cn } from '@/utils/cn'

export interface AdminMetricCardProps {
  label: string
  value: string
  icon?: MetricIconName
  tone?: 'neutral' | 'good' | 'warn' | 'bad'
  size?: 'primary' | 'secondary'
}

export default function AdminMetricCard({
  label,
  value,
  icon,
  tone = 'neutral',
  size = 'primary',
}: AdminMetricCardProps) {
  const isNa = value === 'N/A'

  const valueClass = cn(
    'metric-card__value',
    size === 'primary' ? 'metric-card__value--primary' : 'metric-card__value--secondary',
    isNa && 'metric-card__value--na',
    !isNa && tone === 'good' && 'metric-card__value--good',
    !isNa && tone === 'warn' && 'metric-card__value--warn',
    !isNa && tone === 'bad' && 'metric-card__value--bad',
  )

  const iconTone =
    tone === 'good' ? 'good' : tone === 'warn' ? 'warn' : tone === 'bad' ? 'bad' : 'default'

  return (
    <div className="metric-card">
      <p className="metric-card__label">
        {icon && <MetricIcon name={icon} tone={iconTone} />}
        <span>{label}</span>
      </p>
      <p className={valueClass} aria-label={`${label}: ${value}`}>
        {value}
      </p>
    </div>
  )
}
