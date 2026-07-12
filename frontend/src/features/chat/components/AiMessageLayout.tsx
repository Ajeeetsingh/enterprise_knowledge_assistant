import type { CSSProperties, ReactNode } from 'react'

import { cn } from '@/utils/cn'

import AiAvatar from './AiAvatar'

export interface AiMessageLayoutProps {
  children: ReactNode
  className?: string
  style?: CSSProperties
}

export default function AiMessageLayout({ children, className, style }: AiMessageLayoutProps) {
  return (
    <article
      className={cn('group/message flex w-full animate-message-in justify-start gap-3', className)}
      style={style}
      aria-label="Assistant message"
    >
      <AiAvatar />
      <div className="ai-message-card min-w-0 max-w-[min(88%,42rem)] flex-1 text-sm text-foreground">
        {children}
      </div>
    </article>
  )
}
