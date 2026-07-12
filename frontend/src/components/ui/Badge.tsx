import { type HTMLAttributes } from 'react'

import StatusBadge, { type StatusBadgeTone } from '@/components/ui/StatusBadge'
import { cn } from '@/utils/cn'

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantToTone: Record<BadgeVariant, StatusBadgeTone> = {
  success: 'good',
  warning: 'warn',
  error: 'bad',
  info: 'neutral',
}

export default function Badge({ variant = 'info', className, children, ...props }: BadgeProps) {
  return (
    <StatusBadge tone={variantToTone[variant]} className={cn(className)} {...props}>
      {children}
    </StatusBadge>
  )
}
