import { type HTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  success:
    'bg-success-50 text-success-700 ring-success-500/30 dark:bg-success-700/20 dark:text-success-500',
  warning:
    'bg-warning-50 text-warning-700 ring-warning-500/30 dark:bg-warning-700/20 dark:text-warning-500',
  error:
    'bg-error-50 text-error-700 ring-error-500/30 dark:bg-error-700/20 dark:text-error-500',
  info:
    'bg-info-50 text-info-700 ring-info-500/30 dark:bg-info-700/20 dark:text-info-500',
}

export default function Badge({ variant = 'info', className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5',
        'text-xs font-medium ring-1 ring-inset',
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
