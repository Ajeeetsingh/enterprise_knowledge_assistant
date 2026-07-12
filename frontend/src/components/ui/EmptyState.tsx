import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

export default function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 px-4 py-16 text-center sm:px-6',
        className,
      )}
    >
      {icon && (
        <div className="flex size-12 items-center justify-center rounded-full bg-neutral-100 text-neutral-400 transition-colors duration-200 dark:bg-neutral-800 dark:text-neutral-500">
          {icon}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p className="text-base font-semibold text-neutral-900 dark:text-neutral-50">{title}</p>
        {description && (
          <p className="text-sm leading-relaxed text-neutral-500 dark:text-neutral-400">
            {description}
          </p>
        )}
      </div>

      {action && <div className="w-full">{action}</div>}
    </div>
  )
}
