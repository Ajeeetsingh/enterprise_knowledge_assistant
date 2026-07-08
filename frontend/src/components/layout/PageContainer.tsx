import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface PageContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  /** When true, content spans the full available width without max-width constraint. */
  fullWidth?: boolean
}

export default function PageContainer({
  children,
  fullWidth = false,
  className,
  ...props
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full px-4 py-6 sm:px-6 lg:px-8',
        !fullWidth && 'max-w-7xl',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
