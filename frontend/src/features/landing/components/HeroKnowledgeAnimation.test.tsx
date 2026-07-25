import { render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import HeroKnowledgeAnimation from './HeroKnowledgeAnimation'

describe('HeroKnowledgeAnimation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders as decorative aria-hidden content', () => {
    const { container } = render(<HeroKnowledgeAnimation />)
    const root = container.firstElementChild
    expect(root).toHaveAttribute('aria-hidden', 'true')
    expect(root).toHaveClass('hero-knowledge-anim')
    expect(root).toHaveClass('pointer-events-none')
  })

  it('shows the documents → flow → answer story', () => {
    const { container } = render(<HeroKnowledgeAnimation />)

    expect(container.textContent).toMatch(/HR Policy/)
    expect(container.textContent).toMatch(/Remote Work Policy/)
    expect(container.textContent).toMatch(/Employee Handbook/)
    expect(container.textContent).toMatch(/hybrid-work guidelines/i)
    expect(container.textContent).toMatch(/\[1\] HR Policy/)
    expect(container.textContent).toMatch(/\[2\] Handbook/)
    expect(container.querySelector('.hero-aurora-layer--waves')).toBeTruthy()
    expect(container.querySelector('.hero-aurora-layer--network')).toBeTruthy()
    expect(container.querySelectorAll('.aurora-wave-blob').length).toBeGreaterThanOrEqual(3)
    expect(container.querySelectorAll('.aurora-network-path').length).toBeGreaterThanOrEqual(4)
    expect(container.querySelectorAll('.hero-flow-doc')).toHaveLength(3)
  })

  it('keeps a static composition when reduced motion is preferred', async () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('prefers-reduced-motion'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
        onchange: null,
      })),
    )

    const { container } = render(<HeroKnowledgeAnimation />)

    await waitFor(() => {
      expect(container.firstElementChild).toHaveClass('hero-knowledge-anim--static')
      expect(container.firstElementChild).not.toHaveClass('hero-knowledge-anim--live')
      expect(container.querySelectorAll('animateMotion')).toHaveLength(0)
      expect(container.querySelector('.hero-flow-doc--animate')).toBeNull()
      expect(container.querySelector('.hero-flow-answer--animate')).toBeNull()
      expect(container.textContent).toMatch(/hybrid-work guidelines/i)
    })
  })

  it('enables live motion classes when reduced motion is off', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
        onchange: null,
      })),
    )

    const { container } = render(<HeroKnowledgeAnimation />)
    expect(container.firstElementChild).toHaveClass('hero-knowledge-anim--live')
    expect(container.querySelectorAll('.aurora-network-path--live').length).toBeGreaterThan(0)
    expect(container.querySelectorAll('.hero-flow-doc--animate')).toHaveLength(3)
    expect(container.querySelector('.hero-flow-answer--animate')).toBeTruthy()
  })
})
