import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Reveal, ScrollReveal } from '@/features/landing/components/ScrollReveal'

describe('ScrollReveal', () => {
  it('applies visible class when revealed', () => {
    render(
      <Reveal visible>
        <p>Visible content</p>
      </Reveal>,
    )
    expect(screen.getByText('Visible content').parentElement).toHaveClass('is-visible')
  })

  it('respects reduced motion by revealing immediately', () => {
    const matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }))
    vi.stubGlobal('matchMedia', matchMedia)

    render(
      <ScrollReveal>
        <p>Reduced motion content</p>
      </ScrollReveal>,
    )

    expect(screen.getByText('Reduced motion content').parentElement).toHaveClass('is-visible')
    vi.unstubAllGlobals()
  })
})
