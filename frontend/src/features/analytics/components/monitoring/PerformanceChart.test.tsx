import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import PerformanceChart from './PerformanceChart'

describe('PerformanceChart', () => {
  it('renders performance chart cards', () => {
    render(
      <PerformanceChart
        trends={{
          api_latency: { event_type: 'api_latency', points: {} },
          search_latency: { event_type: 'search_latency', points: { '2026-06-27': 2 } },
          errors: { event_type: 'chat.retrieval.failed', points: { '2026-06-27': 1 } },
          health_events: { event_type: 'health_events', points: { '2026-06-27': 2 } },
          timeline_items: [],
          timeline_total: 0,
          timeline_limit: 10,
          timeline_offset: 0,
          start_date: '2026-06-20T00:00:00Z',
          end_date: '2026-06-27T23:59:59Z',
        }}
      />,
    )

    expect(screen.getByText('Search Latency Trend')).toBeInTheDocument()
    expect(screen.getByText('Error Trend')).toBeInTheDocument()
  })
})
