import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ServiceStatusTable from './ServiceStatusTable'

describe('ServiceStatusTable', () => {
  it('renders service rows', () => {
    render(
      <ServiceStatusTable
        items={[
          {
            service: 'database',
            status: 'healthy',
            detail: 'Database connectivity probe succeeded.',
          },
        ]}
      />,
    )

    expect(screen.getByText('Database')).toBeInTheDocument()
    expect(screen.getByText('healthy')).toBeInTheDocument()
  })

  it('renders empty state', () => {
    render(<ServiceStatusTable items={[]} />)

    expect(screen.getByText('No service status data')).toBeInTheDocument()
  })
})
