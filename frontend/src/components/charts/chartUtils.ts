/** Shared chart color tokens — reference CSS variables from global.css. */

export const CHART_COLORS = {
  primary: 'var(--chart-primary)',
  secondary: 'var(--chart-secondary)',
  tertiary: 'var(--chart-tertiary)',
  success: 'var(--status-good)',
  warning: 'var(--status-warn)',
  danger: 'var(--status-bad)',
  muted: 'var(--text-tertiary)',
} as const

export interface ChartPoint {
  label: string
  value: number
}

export function seriesToChartPoints(points: Record<string, number>): ChartPoint[] {
  return Object.entries(points)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, value]) => ({ label, value }))
}

export function formatChartDateLabel(label: string): string {
  const date = new Date(`${label}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) {
    return label
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function hasInsufficientChartData(data: ChartPoint[]): boolean {
  return data.length <= 1
}
