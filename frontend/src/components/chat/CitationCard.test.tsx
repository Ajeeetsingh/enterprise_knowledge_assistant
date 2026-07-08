import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CitationCard from './CitationCard'
import type { Citation } from '@/features/chat/types'

const sampleCitation: Citation = {
  source: 'Employee Handbook.pdf',
  excerpt: 'Employees are entitled to 20 days of annual leave.',
  confidence: 0.92,
  page: 14,
}

describe('CitationCard', () => {
  it('calls onSelect when clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<CitationCard citation={sampleCitation} onSelect={onSelect} />)

    await user.click(
      screen.getByRole('button', { name: /view citation details for employee handbook\.pdf/i }),
    )

    expect(onSelect).toHaveBeenCalledWith(sampleCitation)
  })

  it('is keyboard accessible', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<CitationCard citation={sampleCitation} onSelect={onSelect} />)

    const button = screen.getByRole('button', {
      name: /view citation details for employee handbook\.pdf/i,
    })
    button.focus()
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith(sampleCitation)
  })
})
