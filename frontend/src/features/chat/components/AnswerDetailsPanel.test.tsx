import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Citation } from '../types'

import AnswerDetailsPanel from './AnswerDetailsPanel'

let isDesktop = false

vi.mock('@/hooks/useMinWidthMediaQuery', () => ({
  useMinWidthMediaQuery: () => isDesktop,
}))

const citations: Citation[] = [
  {
    source: 'Company Overview.pdf',
    excerpt: 'Chief Executive Officer\nEffective Date 01 January 2026',
    confidence: 0.88,
    page: 2,
  },
]

const metadata = {
  confidence_score: 0.88,
  citations,
}

describe('AnswerDetailsPanel', () => {
  it('does not render mobile sheet content when closed', () => {
    isDesktop = false

    render(
      <AnswerDetailsPanel
        panelId="details-panel"
        isOpen={false}
        onClose={() => undefined}
        metadata={metadata}
        onOpenSource={() => undefined}
      />,
    )

    expect(screen.queryByText('Sources')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Answer details' })).not.toBeInTheDocument()
  })

  it('renders mobile sheet in a portal when open', async () => {
    isDesktop = false
    const user = userEvent.setup()
    const onOpenSource = vi.fn()

    render(
      <AnswerDetailsPanel
        panelId="details-panel"
        isOpen
        onClose={() => undefined}
        metadata={metadata}
        onOpenSource={onOpenSource}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: 'Answer details' })
    expect(dialog).toBeInTheDocument()
    expect(dialog.parentElement).toBe(document.body)
    expect(screen.getByText('Company Overview.pdf')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Open Source' }))
    expect(onOpenSource).toHaveBeenCalledWith(citations[0])
  })
})
