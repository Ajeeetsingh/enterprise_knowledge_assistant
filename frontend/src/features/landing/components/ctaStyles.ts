import { cn } from '@/utils/cn'

const focusRing =
  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]'

/** Shared CTA styles matching the design-system Button component. */
export const ctaPrimaryClass = cn(
  'inline-flex items-center justify-center rounded-md font-medium',
  'h-11 px-5 text-sm gap-2 sm:h-12 sm:px-6 sm:text-base',
  'bg-accent text-white shadow-elevation-sm',
  'transition-all duration-150 ease-out',
  'hover:bg-accent-hover active:bg-accent-pressed active:scale-[0.97]',
  focusRing,
)

export const ctaSecondaryClass = cn(
  'inline-flex items-center justify-center rounded-md font-medium',
  'h-11 px-5 text-sm gap-2 sm:h-12 sm:px-6 sm:text-base',
  'border border-border-default bg-transparent text-muted',
  'transition-all duration-150 ease-out',
  'hover:bg-overlay hover:text-foreground active:scale-[0.97]',
  focusRing,
)

export const ctaNavPrimaryClass = cn(
  'inline-flex items-center justify-center rounded-md font-medium',
  'h-8 px-3 text-sm gap-1.5',
  'bg-accent text-white shadow-elevation-sm',
  'transition-all duration-150 ease-out',
  'hover:bg-accent-hover active:bg-accent-pressed active:scale-[0.97]',
  focusRing,
)

export const ctaNavGhostClass = cn(
  'inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium',
  'text-muted transition-colors duration-150',
  'hover:bg-overlay hover:text-foreground',
  focusRing,
)
