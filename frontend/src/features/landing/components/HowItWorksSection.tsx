import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import { Reveal } from './ScrollReveal'

const STEPS = [
  {
    step: '01',
    title: 'Upload documents',
    description:
      'Add policies, handbooks, and procedures in bulk. Supported formats include PDF, DOCX, and TXT.',
  },
  {
    step: '02',
    title: 'Hybrid indexing',
    description:
      'Documents are indexed with dense and keyword retrieval so both meaning and exact terms are findable.',
  },
  {
    step: '03',
    title: 'Ask in plain language',
    description:
      'Teams ask natural questions in chat — no folder hunting or keyword gymnastics required.',
  },
  {
    step: '04',
    title: 'Get cited answers',
    description:
      'Responses stay grounded in authorised sources, with citations you can open and verify.',
  },
] as const

export default function HowItWorksSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()

  return (
    <section
      ref={ref}
      className="relative scroll-mt-20 overflow-hidden px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      id="how-it-works"
      aria-labelledby="landing-how-heading"
    >
      <div aria-hidden className="landing-section-glow" />

      <div className="relative mx-auto max-w-6xl">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-start lg:gap-14">
          <Reveal visible={isVisible} variant="slide-right" className="lg:sticky lg:top-24">
            <p className="landing-eyebrow">How it works</p>
            <h2
              id="landing-how-heading"
              className="landing-section-title font-display text-2xl tracking-tight sm:text-3xl"
            >
              From upload to cited answer
            </h2>
            <p className="mt-4 max-w-md text-base leading-relaxed text-[#475569]">
              A practical retrieval pipeline — not a generic chatbot. Each step maps to capabilities
              already running in the product.
            </p>
          </Reveal>

          <ol className="relative space-y-4">
            <li aria-hidden className="pointer-events-none absolute inset-y-4 left-[1.35rem] hidden list-none sm:block">
              <span className="block h-full w-px bg-gradient-to-b from-[#8B5CF6]/50 via-[#C7D2FE] to-transparent" />
            </li>
            {STEPS.map((item, index) => (
              <Reveal
                key={item.step}
                as="li"
                visible={isVisible}
                variant="slide-left"
                delayMs={120 + index * 90}
              >
                <div className={cn('landing-how-card')}>
                  <span className="landing-how-step">{item.step}</span>
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-[#0F172A]">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-[#475569]">{item.description}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}
