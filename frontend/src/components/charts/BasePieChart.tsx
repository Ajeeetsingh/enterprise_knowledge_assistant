import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import ChartEmptyState from './ChartEmptyState'
import { CHART_COLORS, hasInsufficientChartData, type ChartPoint } from './chartUtils'

const PIE_COLORS = [
  CHART_COLORS.primary,
  CHART_COLORS.secondary,
  CHART_COLORS.tertiary,
  CHART_COLORS.warning,
  CHART_COLORS.danger,
  CHART_COLORS.muted,
]

export interface BasePieChartProps {
  data: ChartPoint[]
  ariaLabel: string
  valueLabel?: string
}

export default function BasePieChart({
  data,
  ariaLabel,
  valueLabel = 'Count',
}: BasePieChartProps) {
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
        <PieChart>
          <Tooltip formatter={(value) => [Number(value ?? 0), valueLabel]} />
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            outerRadius={90}
            label
          >
            {data.map((entry, index) => (
              <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
