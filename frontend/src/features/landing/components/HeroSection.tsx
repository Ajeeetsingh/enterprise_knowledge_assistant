import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import ProductPreview from './ProductPreview'
import { ctaPrimaryClass, ctaSecondaryClass } from './ctaStyles'

function RevealItem({
  visible,
  delayMs,
  className,
  children,
}: {
  visible: boolean
  delayMs: number
  className?: string
  children: ReactNode
}) {
  return (
    <div
      className={cn('landing-reveal', visible && 'is-visible', className)}
      style={{ transitionDelay: visible ? `${delayMs}ms` : undefined }}
    >
      {children}
    </div>
  )
}

export default function HeroSection() {
  const { isAuthenticated, isLoading } = useAuth()
  const [entered, setEntered] = useState(false)
  const showDashboard = !isLoading && isAuthenticated

  useEffect(() => {
    const frame = requestAnimationFrame(() => setEntered(true))
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <section className="relative overflow-hidden px-4 pb-16 pt-10 sm:px-6 sm:pb-20 sm:pt-14 lg:px-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[28rem] bg-[radial-gradient(ellipse_at_top,var(--accent-muted),transparent_60%)]"
      />

      <div className="relative mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          <RevealItem visible={entered} delayMs={0}>
            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
              <span
                aria-hidden
                className="inline-block size-1.5 rounded-full bg-accent shadow-[0_0_0_3px_var(--accent-muted)]"
              />
              AI-Powered Knowledge Platform
            </p>
          </RevealItem>

          <RevealItem visible={entered} delayMs={80} className="mt-5">
            <h1 className="font-display text-[1.85rem] font-semibold leading-[1.15] tracking-tight text-foreground sm:text-4xl sm:leading-[1.12] lg:text-[2.65rem]">
              Ask anything. Get answers from your organisation&apos;s knowledge.
            </h1>
          </RevealItem>

          <RevealItem visible={entered} delayMs={160} className="mt-4">
            <p className="mx-auto max-w-xl text-base leading-relaxed text-muted sm:text-lg">
              Search policies, procedures, and institutional knowledge in seconds — not folders.
            </p>
          </RevealItem>

          <RevealItem
            visible={entered}
            delayMs={240}
            className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
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
          </RevealItem>
        </div>

        <RevealItem visible={entered} delayMs={340} className="mt-12 sm:mt-14">
          <ProductPreview />
        </RevealItem>
      </div>
    </section>
  )
}
