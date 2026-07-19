import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import { ctaPrimaryClass, ctaSecondaryClass } from './ctaStyles'

export default function FinalCtaSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()
  const { isAuthenticated, isLoading } = useAuth()
  const showDashboard = !isLoading && isAuthenticated

  return (
    <section
      ref={ref}
      className="px-4 pb-16 sm:px-6 sm:pb-20 lg:px-8"
      aria-labelledby="landing-final-cta-heading"
    >
      <div
        className={cn(
          'landing-reveal relative mx-auto max-w-6xl overflow-hidden rounded-[var(--radius-lg)]',
          'border border-border-default bg-surface-raised px-6 py-12 text-center shadow-elevation-md',
          'sm:px-10 sm:py-14',
          isVisible && 'is-visible',
        )}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,var(--accent-muted),transparent_65%)]"
        />

        <div className="relative">
          <h2
            id="landing-final-cta-heading"
            className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
          >
            Stop searching. Start asking.
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-base text-muted">
            Put your organisation&apos;s knowledge to work — with answers you can trust and sources
            you can verify.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {showDashboard ? (
              <Link to="/dashboard" className={ctaPrimaryClass}>
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/register" className={ctaPrimaryClass}>
                  Get Started
                </Link>
                <Link to="/login" className={ctaSecondaryClass}>
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
