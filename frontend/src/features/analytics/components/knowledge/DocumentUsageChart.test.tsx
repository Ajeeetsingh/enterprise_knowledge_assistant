import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import DocumentUsageChart from './DocumentUsageChart'

describe('DocumentUsageChart', () => {
  it('renders chart card with data', () => {
    render(
      <DocumentUsageChart
        documents={{
          most_viewed: [],
          least_viewed: [],
          total_most_viewed: 0,
          total_least_viewed: 0,
          average_document_views: null,
          average_citations_per_document: null,
          document_usage_trend: {
            event_type: 'document_usage',
            points: { '2026-06-27': 3 },
          },
          start_date: '2026-06-20T00:00:00Z',
          end_date: '2026-06-27T23:59:59Z',
        }}
      />,
    )

    expect(screen.getByText('Document Usage')).toBeInTheDocument()
  })
})
