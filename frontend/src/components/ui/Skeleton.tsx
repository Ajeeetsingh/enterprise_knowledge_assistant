import { type HTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** Rounded variant for circular placeholders. */
  variant?: 'rect' | 'circle' | 'text'
}

export default function Skeleton({
  variant = 'rect',
  className,
  ...props
}: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        'skeleton-shimmer bg-neutral-200 dark:bg-neutral-800',
        variant === 'circle' && 'rounded-full',
        variant === 'text' && 'h-3 rounded',
        variant === 'rect' && 'rounded-md',
        className,
      )}
      {...props}
    />
  )
}
