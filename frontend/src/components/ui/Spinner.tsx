import { cn } from '@/utils/cn'

export type SpinnerSize = 'sm' | 'md' | 'lg'

export interface SpinnerProps {
  size?: SpinnerSize
  className?: string
  label?: string
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'size-4 border-2',
  md: 'size-6 border-2',
  lg: 'size-10 border-4',
}

export default function Spinner({ size = 'md', className, label = 'Loading…' }: SpinnerProps) {
  return (
    <span role="status" aria-label={label} className="inline-flex items-center justify-center">
      <span
        aria-hidden
        className={cn(
          'animate-spin rounded-full border-current border-t-transparent text-primary-600 dark:text-primary-400',
          sizeClasses[size],
          className,
        )}
      />
    </span>
  )
}
