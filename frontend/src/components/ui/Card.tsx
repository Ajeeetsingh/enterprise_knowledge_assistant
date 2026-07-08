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
        'rounded-lg border border-neutral-200 bg-white shadow-sm',
        'dark:border-neutral-700 dark:bg-neutral-900',
        className,
      )}
      {...props}
    >
      {title && (
        <div className="border-b border-neutral-200 px-6 py-4 dark:border-neutral-700">
          {typeof title === 'string' ? (
            <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">
              {title}
            </h3>
          ) : (
            title
          )}
        </div>
      )}

      <div className="px-6 py-5">{children}</div>

      {footer && (
        <div className="border-t border-neutral-200 px-6 py-4 dark:border-neutral-700">
          {footer}
        </div>
      )}
    </div>
  )
}
