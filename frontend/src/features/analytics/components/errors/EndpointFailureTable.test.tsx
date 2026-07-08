import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import EndpointFailureTable from './EndpointFailureTable'

describe('EndpointFailureTable', () => {
  it('renders endpoint rows', () => {
    render(
      <EndpointFailureTable
        items={[{ endpoint: '/api/v1/chat', count: 2, service: 'ai_service' }]}
      />,
    )

    expect(screen.getByText('/api/v1/chat')).toBeInTheDocument()
    expect(screen.getByText('ai_service')).toBeInTheDocument()
  })

  it('renders empty state', () => {
    render(<EndpointFailureTable items={[]} />)

    expect(screen.getByText('No endpoint failures recorded')).toBeInTheDocument()
  })
})
