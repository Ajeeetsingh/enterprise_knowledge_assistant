import {
  createElement,
  forwardRef,
  type ElementType,
  type HTMLAttributes,
  type ReactNode,
} from 'react'

import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'

export type RevealVariant = 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right'

export interface RevealProps extends HTMLAttributes<HTMLElement> {
  visible: boolean
  variant?: RevealVariant
  delayMs?: number
  as?: ElementType
  children: ReactNode
}

/**
 * Presentational reveal — apply CSS entrance when *visible* becomes true.
 * Use with a parent section’s IntersectionObserver for staggered groups.
 */
export const Reveal = forwardRef<HTMLElement, RevealProps>(function Reveal(
  {
    visible,
    variant = 'fade-up',
    delayMs = 0,
    as: Component = 'div',
    className,
    children,
    style,
    ...rest
  },
  ref,
) {
  return createElement(
    Component,
    {
      ref,
      className: cn(
        'landing-reveal',
        `landing-reveal--${variant}`,
        visible && 'is-visible',
        className,
      ),
      style: {
        ...style,
        transitionDelay: visible && delayMs > 0 ? `${delayMs}ms` : undefined,
      },
      ...rest,
    },
    children,
  )
})

export interface ScrollRevealProps extends Omit<RevealProps, 'visible'> {
  /** Optional threshold override is not exposed — keep IO config centralized. */
}

/**
 * Self-observing reveal for standalone blocks.
 * Prefer a single section observer + {@link Reveal} for card grids (fewer observers).
 */
export function ScrollReveal({
  variant = 'fade-up',
  delayMs = 0,
  as = 'div',
  className,
  children,
  ...rest
}: ScrollRevealProps) {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()

  return (
    <Reveal
      ref={ref}
      visible={isVisible}
      variant={variant}
      delayMs={delayMs}
      as={as}
      className={className}
      {...rest}
    >
      {children}
    </Reveal>
  )
}
