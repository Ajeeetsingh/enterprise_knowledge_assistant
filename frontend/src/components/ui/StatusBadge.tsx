import { type HTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

export type StatusBadgeTone = 'good' | 'warn' | 'bad' | 'neutral'

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: StatusBadgeTone
}

const toneClasses: Record<StatusBadgeTone, string> = {
  good: 'status-badge--good',
  warn: 'status-badge--warn',
  bad: 'status-badge--bad',
  neutral: 'status-badge--neutral',
}

export default function StatusBadge({
  tone = 'neutral',
  className,
  children,
  ...props
}: StatusBadgeProps) {
  return (
    <span className={cn('status-badge', toneClasses[tone], className)} {...props}>
      {children}
    </span>
  )
}
