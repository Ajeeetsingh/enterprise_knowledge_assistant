import {
  CartesianGrid,
  Line,
  LineChart,
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

export interface BaseLineChartProps {
  data: ChartPoint[]
  color?: string
  ariaLabel: string
  valueLabel?: string
}

export default function BaseLineChart({
  data,
  color = CHART_COLORS.primary,
  ariaLabel,
  valueLabel = 'Count',
}: BaseLineChartProps) {
  if (hasInsufficientChartData(data)) {
    return (
      <ChartEmptyState
        message={
          data.length === 0 ? 'No data for the selected period' : 'No activity in this range'
        }
      />
    )
  }

  return (
    <div role="img" aria-label={ariaLabel} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
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
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3, fill: color }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
