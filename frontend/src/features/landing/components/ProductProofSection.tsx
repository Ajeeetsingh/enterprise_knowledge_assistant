import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import { Reveal } from './ScrollReveal'

/**
 * Capability callouts — not external customer metrics.
 * Numeric product KPIs are omitted because the repo does not publish
 * stable, visitor-facing benchmark figures suitable for marketing claims.
 */
const CAPABILITIES = [
  {
    label: 'Hybrid',
    detail: 'Dense + keyword retrieval',
  },
  {
    label: 'Grounded',
    detail: 'Answers backed by source documents',
  },
  {
    label: 'Secure',
    detail: 'Role-aware document access',
  },
] as const

export default function ProductProofSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()

  return (
    <section
      ref={ref}
      className="relative overflow-hidden px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="landing-proof-heading"
    >
      <div aria-hidden className="landing-section-glow" />

      <div className="relative mx-auto max-w-6xl">
        <Reveal visible={isVisible} className={cn('landing-proof-shell')}>
          <div className="border-b border-[rgba(99,102,241,0.1)] px-6 py-10 text-center sm:px-10 sm:py-12">
            <h2
              id="landing-proof-heading"
              className="landing-section-title font-display text-2xl tracking-tight sm:text-3xl"
            >
              Why teams use this
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-[#475569]">
              A retrieval stack designed for accuracy, traceability, and controlled access —
              not another chatbot wrapping a search box.
            </p>
          </div>

          <ul className="grid divide-y divide-[rgba(99,102,241,0.1)] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {CAPABILITIES.map((item, index) => (
              <Reveal
                key={item.label}
                as="li"
                visible={isVisible}
                delayMs={140 + index * 90}
                className="px-6 py-9 text-center sm:px-8"
              >
                <p className="landing-proof-label">{item.label}</p>
                <p className="mt-3 text-sm leading-relaxed text-[#475569]">{item.detail}</p>
              </Reveal>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}
