/** Shared chart color tokens for analytics dashboards. */

export const CHART_COLORS = {
  primary: '#2563eb',
  secondary: '#7c3aed',
  success: '#16a34a',
  warning: '#d97706',
  danger: '#dc2626',
  muted: '#94a3b8',
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
