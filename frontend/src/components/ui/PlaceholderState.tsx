import { type ReactNode } from 'react'

import { cn } from '@/utils/cn'

export interface PlaceholderStateProps {
  children: ReactNode
  className?: string
}

export default function PlaceholderState({ children, className }: PlaceholderStateProps) {
  return <div className={cn('empty-state-placeholder', className)}>{children}</div>
}
