import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ChartEmptyState from './ChartEmptyState'
import {
  CHART_COLORS,
  formatChartDateLabel,
  hasInsufficientChartData,
  type ChartPoint,
} from './chartUtils'

export interface BaseAreaChartProps {
  data: ChartPoint[]
  color?: string
  ariaLabel: string
  valueLabel?: string
}

export default function BaseAreaChart({
  data,
  color = CHART_COLORS.primary,
  ariaLabel,
  valueLabel = 'Count',
}: BaseAreaChartProps) {
  if (hasInsufficientChartData(data)) {
    return (
      <ChartEmptyState
        message={
          data.length === 0 ? 'No data for the selected period' : 'No activity in this range'
        }
      />
    )
  }

  const gradientId = `area-gradient-${ariaLabel.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <div role="img" aria-label={ariaLabel} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="var(--border-subtle)"
            strokeDasharray="2 4"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            tickFormatter={formatChartDateLabel}
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [Number(value ?? 0), valueLabel]}
            labelFormatter={(label) => formatChartDateLabel(String(label))}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={`url(#${gradientId})`}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
