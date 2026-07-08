import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_COLORS, formatChartDateLabel, type ChartPoint } from './chartUtils'

export interface BaseAreaChartProps {
  data: ChartPoint[]
  color?: string
  ariaLabel: string
  valueLabel?: string
}

export default function BaseAreaChart({
  data,
  color = CHART_COLORS.success,
  ariaLabel,
  valueLabel = 'Count',
}: BaseAreaChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex h-64 items-center justify-center text-sm text-neutral-500 dark:text-neutral-400"
        role="img"
        aria-label={`${ariaLabel}: no data`}
      >
        No data for the selected period.
      </div>
    )
  }

  return (
    <div role="img" aria-label={ariaLabel} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-neutral-200 dark:stroke-neutral-700" />
          <XAxis
            dataKey="label"
            tickFormatter={formatChartDateLabel}
            tick={{ fontSize: 12 }}
            stroke="currentColor"
            className="text-neutral-500 dark:text-neutral-400"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12 }}
            stroke="currentColor"
            className="text-neutral-500 dark:text-neutral-400"
          />
          <Tooltip
            formatter={(value) => [Number(value ?? 0), valueLabel]}
            labelFormatter={(label) => formatChartDateLabel(String(label))}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
