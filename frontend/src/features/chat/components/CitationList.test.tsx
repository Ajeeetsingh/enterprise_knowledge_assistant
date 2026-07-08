import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CitationList from './CitationList'
import type { Citation } from '../types'

vi.mock('../services/citationService', () => ({
  CitationDetailsError: class CitationDetailsError extends Error {},
  resolveCitationDetails: vi.fn(async (citation: Citation) => ({
    source: citation.source,
    excerpt: citation.excerpt?.trim() ? citation.excerpt.trim() : null,
    confidence: citation.confidence,
    page: citation.page ?? null,
    metadata: citation.metadata,
  })),
}))

const citations: Citation[] = [
  {
    source: 'Employee Handbook.pdf',
    excerpt: 'Employees are entitled to 20 days of annual leave.',
    confidence: 0.92,
    page: 14,
  },
]

describe('CitationList', () => {
  it('opens the citation modal when a card is clicked', async () => {
    const user = userEvent.setup()

    render(<CitationList citations={citations} />)

    await user.click(
      screen.getByRole('button', { name: /view citation details for employee handbook\.pdf/i }),
    )

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /citation details/i })).toBeInTheDocument()
    })

    expect(
      screen.getByText('Employees are entitled to 20 days of annual leave.'),
    ).toBeInTheDocument()
  })

  it('closes the citation modal', async () => {
    const user = userEvent.setup()

    render(<CitationList citations={citations} />)

    await user.click(
      screen.getByRole('button', { name: /view citation details for employee handbook\.pdf/i }),
    )

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /citation details/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Close citation details' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /citation details/i })).not.toBeInTheDocument()
    })
  })
})
