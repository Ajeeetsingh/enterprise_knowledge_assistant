import type { ComponentType } from 'react'

import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import {
  FileTextIcon,
  MessageSquareIcon,
  ShieldCheckIcon,
  UploadCloudIcon,
} from './LandingIcons'
import { Reveal } from './ScrollReveal'

const FEATURES: Array<{
  title: string
  description: string
  Icon: ComponentType<{ className?: string }>
}> = [
  {
    title: 'Natural-language answers',
    description:
      'Ask questions in plain English and get clear, grounded answers instantly.',
    Icon: MessageSquareIcon,
  },
  {
    title: 'Cited from your documents',
    description:
      'Every answer connects back to the documents and sources used to generate it.',
    Icon: FileTextIcon,
  },
  {
    title: 'Upload in bulk',
    description:
      'Build your knowledge base by uploading and processing multiple documents.',
    Icon: UploadCloudIcon,
  },
  {
    title: 'Enterprise-grade access',
    description:
      'Role-based permissions keep sensitive knowledge accessible only to the right users.',
    Icon: ShieldCheckIcon,
  },
]

export default function FeaturesSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()

  return (
    <section
      ref={ref}
      className="landing-features relative scroll-mt-20 overflow-hidden border-t border-border-subtle px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      id="features"
      aria-labelledby="landing-features-heading"
    >
      <div
        aria-hidden
        className="landing-features-glow pointer-events-none absolute inset-0"
      />

      <div className="relative mx-auto max-w-6xl py-2">
        <Reveal visible={isVisible} className="mx-auto max-w-2xl text-center">
          <h2
            id="landing-features-heading"
            className="landing-section-title font-display text-2xl tracking-[-0.02em] sm:text-3xl"
          >
            Built for organisational knowledge
          </h2>
          <p className="mt-3 text-base font-medium leading-relaxed text-[#475569]">
            Everything your team needs to turn documents into reliable, citeable answers.
          </p>
        </Reveal>

        <ul className="relative mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">
          {FEATURES.map((feature, index) => (
            <Reveal
              key={feature.title}
              as="li"
              visible={isVisible}
              delayMs={100 + index * 75}
            >
              <div className="landing-feature-card group h-full p-5">
                <span
                  className={cn('landing-feature-icon', `landing-feature-icon--${index + 1}`)}
                >
                  <feature.Icon className="size-[22px]" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-[#0F172A]">{feature.title}</h3>
                <p className="mt-2 text-sm font-medium leading-relaxed text-[#475569]">
                  {feature.description}
                </p>
              </div>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  )
}
