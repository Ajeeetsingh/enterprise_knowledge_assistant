import { cn } from '@/utils/cn'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface ToastProps {
  id: string
  variant: ToastVariant
  message: string
  onDismiss: (id: string) => void
}

const VARIANT_STYLES: Record<
  ToastVariant,
  { container: string; icon: string; label: string }
> = {
  success: {
    container:
      'border-success-500/30 bg-success-50 text-success-700 dark:bg-success-700/10 dark:text-success-400',
    icon: '✓',
    label: 'Success',
  },
  error: {
    container:
      'border-error-500/30 bg-error-50 text-error-700 dark:bg-error-700/10 dark:text-error-400',
    icon: '!',
    label: 'Error',
  },
  warning: {
    container:
      'border-warning-500/30 bg-warning-50 text-warning-700 dark:bg-warning-700/10 dark:text-warning-400',
    icon: '!',
    label: 'Warning',
  },
  info: {
    container:
      'border-info-500/30 bg-info-50 text-info-700 dark:bg-info-700/10 dark:text-info-400',
    icon: 'i',
    label: 'Information',
  },
}

export default function Toast({ id, variant, message, onDismiss }: ToastProps) {
  const styles = VARIANT_STYLES[variant]
  const isAssertive = variant === 'error' || variant === 'warning'

  return (
    <div
      role="alert"
      aria-live={isAssertive ? 'assertive' : 'polite'}
      aria-atomic="true"
      className={cn(
        'flex w-full max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-lg',
        styles.container,
      )}
    >
      <span
        aria-hidden
        className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-current/10 text-xs font-bold"
      >
        {styles.icon}
      </span>

      <div className="min-w-0 flex-1">
        <p className="sr-only">{styles.label}</p>
        <p className="text-sm font-medium">{message}</p>
      </div>

      <button
        type="button"
        aria-label="Dismiss notification"
        className={cn(
          'shrink-0 rounded-md p-1 text-current opacity-70 transition-opacity',
          'hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current',
        )}
        onClick={() => onDismiss(id)}
      >
        <span aria-hidden>×</span>
      </button>
    </div>
  )
}
