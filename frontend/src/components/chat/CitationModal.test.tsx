import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CitationModal from './CitationModal'
import type { CitationDetails } from '@/features/chat/types'

const sampleDetails: CitationDetails = {
  source: 'Employee Handbook.pdf',
  excerpt: 'Employees are entitled to 20 days of annual leave.',
  confidence: 0.92,
  page: 14,
}

describe('CitationModal', () => {
  it('renders citation excerpt and metadata fields', () => {
    render(
      <CitationModal
        isOpen
        details={sampleDetails}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByRole('dialog', { name: /citation details/i })).toBeInTheDocument()
    expect(screen.getByText('Employee Handbook.pdf')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(
      screen.getByText('Employees are entitled to 20 days of annual leave.'),
    ).toBeInTheDocument()
  })

  it('shows missing excerpt state', () => {
    render(
      <CitationModal
        isOpen
        details={{ ...sampleDetails, excerpt: null }}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText('No excerpt available.')).toBeInTheDocument()
  })

  it('shows missing page state', () => {
    render(
      <CitationModal
        isOpen
        details={{ ...sampleDetails, page: null }}
        isLoading={false}
        error={null}
        onClose={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText('Page information unavailable.')).toBeInTheDocument()
  })

  it('shows error state with retry', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <CitationModal
        isOpen
        details={null}
        isLoading={false}
        error="Unable to load citation details."
        onClose={vi.fn()}
        onRetry={onRetry}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('closes on escape and backdrop interactions', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    render(
      <CitationModal
        isOpen
        details={sampleDetails}
        isLoading={false}
        error={null}
        onClose={onClose}
        onRetry={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Close citation details' }))
    expect(onClose).toHaveBeenCalledTimes(1)

    onClose.mockClear()
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
