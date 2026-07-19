import { type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode
  footer?: ReactNode
}

export default function Card({ title, footer, children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'overflow-hidden rounded-[var(--radius-lg)] border border-border-subtle',
        'bg-surface-raised shadow-elevation-md',
        className,
      )}
      {...props}
    >
      {title && (
        <div className="border-b border-border-subtle px-8 py-5">
          {typeof title === 'string' ? (
            <h3 className="text-base font-semibold text-foreground">{title}</h3>
          ) : (
            title
          )}
        </div>
      )}

      <div className="px-8 py-8">{children}</div>

      {footer && (
        <div className="border-t border-border-subtle px-8 py-5">{footer}</div>
      )}
    </div>
  )
}
