import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CitationCard from './CitationCard'
import type { Citation } from '@/features/chat/types'

const sampleCitation: Citation = {
  source: 'Employee Handbook.pdf',
  excerpt: 'Remote work policy applies to all full-time employees.',
  confidence: 0.91,
  page: 13,
}

describe('CitationCard', () => {
  it('calls onOpenSource when clicked', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()

    render(<CitationCard citation={sampleCitation} onOpenSource={onOpenSource} />)

    await user.click(
      screen.getByRole('button', { name: 'Open source document for Employee Handbook.pdf' }),
    )

    expect(onOpenSource).toHaveBeenCalledWith(sampleCitation)
  })

  it('shows Open Source label', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()

    render(<CitationCard citation={sampleCitation} onOpenSource={onOpenSource} />)

    expect(screen.getByText('Open Source')).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Open source document for Employee Handbook.pdf' }),
    )
    expect(onOpenSource).toHaveBeenCalledWith(sampleCitation)
  })
})
