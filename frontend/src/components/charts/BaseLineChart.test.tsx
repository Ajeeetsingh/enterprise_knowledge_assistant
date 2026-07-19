import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import BaseLineChart from './BaseLineChart'

describe('BaseLineChart', () => {
  it('renders an empty state when no data is available', () => {
    render(<BaseLineChart data={[]} ariaLabel="Empty trend chart" />)

    // Empty charts use ChartEmptyState with a period message as the accessible name.
    expect(screen.getByLabelText('No data for the selected period')).toBeInTheDocument()
    expect(screen.getByText('No data for the selected period')).toBeInTheDocument()
  })

  it('renders a chart container when data is available', () => {
    render(
      <BaseLineChart
        data={[
          { label: '2026-06-26', value: 3 },
          { label: '2026-06-27', value: 5 },
        ]}
        ariaLabel="Sample trend chart"
      />,
    )

    expect(screen.getByLabelText('Sample trend chart')).toBeInTheDocument()
  })
})
