import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'

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
      className="px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="landing-proof-heading"
    >
      <div className="mx-auto max-w-6xl">
        <div
          className={cn(
            'landing-reveal overflow-hidden rounded-[var(--radius-lg)] border border-border-default',
            'bg-surface-raised shadow-elevation-md',
            isVisible && 'is-visible',
          )}
        >
          <div className="border-b border-border-subtle px-6 py-8 text-center sm:px-10 sm:py-10">
            <h2
              id="landing-proof-heading"
              className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
            >
              Why teams use this
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-muted">
              A retrieval stack designed for accuracy, traceability, and controlled access —
              not another chatbot wrapping a search box.
            </p>
          </div>

          <ul className="grid divide-y divide-border-subtle sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {CAPABILITIES.map((item, index) => (
              <li
                key={item.label}
                className={cn(
                  'landing-reveal px-6 py-8 text-center sm:px-8',
                  isVisible && 'is-visible',
                )}
                style={{
                  transitionDelay: isVisible ? `${140 + index * 80}ms` : undefined,
                }}
              >
                <p className="font-display text-3xl font-semibold tracking-tight text-accent sm:text-4xl">
                  {item.label}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-muted">{item.detail}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
