import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import AnalyticsKPICard from './AnalyticsKPICard'

describe('AnalyticsKPICard', () => {
  it('renders formatted KPI values', () => {
    render(<AnalyticsKPICard label="Daily Active Users" value={128} />)

    expect(screen.getByLabelText('Daily Active Users: 128')).toBeInTheDocument()
  })

  it('renders percent values', () => {
    render(<AnalyticsKPICard label="Active User %" value={42.5} format="percent" />)

    expect(screen.getByLabelText('Active User %: 42.5%')).toBeInTheDocument()
  })
})
