import { type ReactNode } from 'react'

export interface ChartEmptyStateProps {
  message?: string
  icon?: ReactNode
}

function DefaultChartIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="size-8 text-subtle"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 19h16M6 16l3-5 3 3 4-7 3 4" />
    </svg>
  )
}

export default function ChartEmptyState({
  message = 'No activity in this range',
  icon,
}: ChartEmptyStateProps) {
  return (
    <div className="chart-empty-state" role="img" aria-label={message}>
      {icon ?? <DefaultChartIcon />}
      <p>{message}</p>
    </div>
  )
}
