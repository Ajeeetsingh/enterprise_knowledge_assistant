import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import HeroKnowledgeAnimation from './HeroKnowledgeAnimation'
import { Reveal } from './ScrollReveal'
import { ctaPrimaryClass, ctaSecondaryClass } from './ctaStyles'

export default function HeroSection() {
  const { isAuthenticated, isLoading } = useAuth()
  const [entered, setEntered] = useState(false)
  const showDashboard = !isLoading && isAuthenticated

  useEffect(() => {
    const frame = requestAnimationFrame(() => setEntered(true))
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <section className="hero-section relative overflow-hidden px-4 pb-8 pt-10 sm:px-6 sm:pb-10 sm:pt-12 lg:px-8 lg:pb-12">
      {/* Decorative wave + light-trail layers sit behind CTAs */}
      <HeroKnowledgeAnimation />

      <div className="relative z-10 mx-auto max-w-6xl">
        <div className="mx-auto flex max-w-[24rem] flex-col items-center text-center sm:max-w-2xl lg:max-w-3xl">
          <Reveal visible={entered} delayMs={0}>
            <p
              className={cn(
                'inline-flex items-center gap-2 rounded-full',
                'border border-[rgba(109,40,217,0.14)] bg-[#ECE9FE]',
                'px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-[0.08em]',
                'text-[#6D28D9]',
              )}
            >
              <span
                aria-hidden
                className="inline-block size-1.5 rounded-full bg-[#6D28D9]"
              />
              AI-Powered Knowledge Platform
            </p>
          </Reveal>

          <Reveal visible={entered} delayMs={90} className="mt-6 sm:mt-7">
            <h1
              aria-label="Ask anything. Get answers from your organisation's knowledge."
              className="hero-headline font-display text-[1.85rem] font-extrabold leading-[1.12] tracking-[-0.03em] sm:text-4xl sm:leading-[1.1] lg:text-[2.85rem]"
            >
              Ask anything. Get answers
              <br />
              from your organisation&apos;s
              <br />
              <span className="hero-knowledge-gradient">knowledge.</span>
            </h1>
          </Reveal>

          <Reveal
            visible={entered}
            delayMs={180}
            className="mt-4 flex flex-col items-center justify-center gap-3 sm:mt-5 sm:flex-row"
          >
            {showDashboard ? (
              <Link to="/dashboard" className={ctaPrimaryClass}>
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/demo" className={ctaPrimaryClass}>
                  Try Knowra
                  <span aria-hidden className="text-base leading-none">
                    →
                  </span>
                </Link>
                <Link to="/login" className={ctaSecondaryClass}>
                  Sign In
                </Link>
              </>
            )}
          </Reveal>
        </div>

        {/* Compact flow zone — aurora + cards sit immediately under CTA */}
        <div className="hero-flow-spacer" aria-hidden="true" />
      </div>
    </section>
  )
}
