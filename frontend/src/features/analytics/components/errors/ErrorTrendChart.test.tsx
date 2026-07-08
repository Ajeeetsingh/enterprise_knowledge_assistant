import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ErrorTrendChart from './ErrorTrendChart'

describe('ErrorTrendChart', () => {
  it('renders error trend chart cards', () => {
    render(
      <ErrorTrendChart
        trends={{
          total_errors: { event_type: 'total_errors', points: { '2026-06-27': 3 } },
          authentication_failures: { event_type: 'auth.login.failed', points: {} },
          retrieval_failures: { event_type: 'chat.retrieval.failed', points: { '2026-06-27': 1 } },
          upload_failures: { event_type: 'upload_failures', points: {} },
          api_exceptions: { event_type: 'api_exceptions', points: {} },
          permission_denials: { event_type: 'security.permission.denied', points: {} },
          start_date: '2026-06-20T00:00:00Z',
          end_date: '2026-06-27T23:59:59Z',
        }}
      />,
    )

    expect(screen.getByText('Total Errors')).toBeInTheDocument()
    expect(screen.getByText('Retrieval Failures')).toBeInTheDocument()
  })
})
