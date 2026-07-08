import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useCitationDetails } from './useCitationDetails'
import { CitationDetailsError } from '../services/citationService'
import type { Citation } from '../types'

vi.mock('../services/citationService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/citationService')>()
  return {
    ...actual,
    resolveCitationDetails: vi.fn(),
  }
})

import { resolveCitationDetails } from '../services/citationService'

function TestHarness({ citation }: { citation: Citation | null }) {
  const { details, isLoading, error, retry } = useCitationDetails(citation)

  return (
    <div>
      <p data-testid="loading">{isLoading ? 'loading' : 'idle'}</p>
      <p data-testid="error">{error ?? 'none'}</p>
      <p data-testid="excerpt">{details?.excerpt ?? 'none'}</p>
      <button type="button" onClick={retry}>
        Retry
      </button>
    </div>
  )
}

describe('useCitationDetails', () => {
  it('surfaces error state when resolution fails', async () => {
    vi.mocked(resolveCitationDetails).mockRejectedValueOnce(new CitationDetailsError())

    render(
      <TestHarness
        citation={{
          source: 'Broken.pdf',
          excerpt: '',
          confidence: 0.5,
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Unable to load citation details.')
    })
  })
})
