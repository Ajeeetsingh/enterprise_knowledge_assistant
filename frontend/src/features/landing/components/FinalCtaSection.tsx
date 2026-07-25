import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import { Reveal } from './ScrollReveal'
import { ctaPrimaryClass } from './ctaStyles'

export default function FinalCtaSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()
  const { isAuthenticated, isLoading } = useAuth()
  const showDashboard = !isLoading && isAuthenticated

  return (
    <section
      ref={ref}
      className="relative overflow-hidden px-4 pb-20 pt-4 sm:px-6 sm:pb-24 lg:px-8"
      aria-labelledby="landing-final-cta-heading"
    >
      <Reveal
        visible={isVisible}
        className={cn(
          'relative mx-auto max-w-6xl overflow-hidden rounded-[var(--radius-lg)]',
          'border border-border-default bg-surface-raised px-6 py-14 text-center shadow-elevation-md',
          'sm:px-12 sm:py-16',
        )}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,var(--accent-muted),transparent_62%)]"
        />
        <div
          aria-hidden
          className="landing-ambient left-1/2 top-0 hidden h-40 w-[28rem] -translate-x-1/2 bg-[color-mix(in_srgb,var(--accent)_22%,transparent)] sm:block"
        />

        <div className="relative">
          <h2
            id="landing-final-cta-heading"
            className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
          >
            Stop searching. Start asking.
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-base text-muted">
            Put your organisation&apos;s knowledge to work — with answers you can trust and sources
            you can verify.
          </p>

          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {showDashboard ? (
              <Link to="/dashboard" className={ctaPrimaryClass}>
                Go to Dashboard
              </Link>
            ) : (
              <Link to="/demo" className={ctaPrimaryClass}>
                Try the Demo
              </Link>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  )
}
