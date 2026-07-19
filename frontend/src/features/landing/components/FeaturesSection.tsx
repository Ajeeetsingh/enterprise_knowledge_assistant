import type { ComponentType } from 'react'

import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import {
  FileTextIcon,
  MessageSquareIcon,
  ShieldCheckIcon,
  UploadCloudIcon,
} from './LandingIcons'

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
      className="border-t border-border-subtle px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="landing-features-heading"
    >
      <div className="mx-auto max-w-6xl">
        <div
          className={cn(
            'landing-reveal mx-auto max-w-2xl text-center',
            isVisible && 'is-visible',
          )}
        >
          <h2
            id="landing-features-heading"
            className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
          >
            Built for organisational knowledge
          </h2>
          <p className="mt-3 text-base text-muted">
            Everything your team needs to turn documents into reliable, citeable answers.
          </p>
        </div>

        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">
          {FEATURES.map((feature, index) => (
            <li
              key={feature.title}
              className={cn('landing-reveal', isVisible && 'is-visible')}
              style={{
                transitionDelay: isVisible ? `${120 + index * 70}ms` : undefined,
              }}
            >
              <div
                className={cn(
                  'group h-full rounded-[var(--radius-lg)] border border-border-subtle',
                  'bg-surface-raised p-5 shadow-elevation-sm',
                  'transition-[border-color,box-shadow,transform] duration-200',
                  'hover:-translate-y-0.5 hover:border-border-default hover:shadow-elevation-md',
                )}
              >
                <span
                  className={cn(
                    'inline-flex size-10 items-center justify-center rounded-md',
                    'border border-border-subtle bg-overlay text-accent',
                  )}
                >
                  <feature.Icon />
                </span>
                <h3 className="mt-4 text-base font-semibold text-foreground">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{feature.description}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
