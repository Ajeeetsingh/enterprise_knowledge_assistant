import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import BaseLineChart from './BaseLineChart'

describe('BaseLineChart', () => {
  it('renders an empty state when no data is available', () => {
    render(<BaseLineChart data={[]} ariaLabel="Empty trend chart" />)

    expect(screen.getByLabelText('Empty trend chart: no data')).toBeInTheDocument()
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
