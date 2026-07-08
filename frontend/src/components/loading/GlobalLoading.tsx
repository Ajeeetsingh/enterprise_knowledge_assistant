import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

export interface GlobalLoadingProps {
  isVisible: boolean
  message?: string
  className?: string
}

export default function GlobalLoading({
  isVisible,
  message = 'Loading…',
  className,
}: GlobalLoadingProps) {
  if (!isVisible) return null

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        'fixed inset-0 z-[90] flex items-center justify-center bg-black/40 px-4',
        className,
      )}
    >
      <div className="flex flex-col items-center gap-3 rounded-lg border border-neutral-200 bg-white px-8 py-6 shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
        <Spinner size="lg" label={message} />
        <p className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{message}</p>
      </div>
    </div>
  )
}
