import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, id, className, disabled, ...props }, ref) => {
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)
    const hasError = Boolean(error)

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-neutral-700 dark:text-neutral-200"
          >
            {label}
          </label>
        )}

        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          aria-invalid={hasError}
          aria-describedby={
            hasError ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
          }
          className={cn(
            'block w-full rounded-md border px-3 py-2 text-sm',
            'placeholder:text-neutral-400',
            'transition-colors duration-150',
            'focus:outline-none focus:ring-2 focus:ring-offset-1',
            'disabled:cursor-not-allowed disabled:opacity-50',
            hasError
              ? 'border-error-500 focus:ring-error-500 text-error-700 dark:text-error-400'
              : 'border-neutral-300 focus:ring-primary-500 text-neutral-900 dark:text-neutral-50',
            'bg-white dark:bg-neutral-800 dark:border-neutral-600',
            className,
          )}
          {...props}
        />

        {hint && !hasError && (
          <p id={`${inputId}-hint`} className="text-xs text-neutral-500 dark:text-neutral-400">
            {hint}
          </p>
        )}

        {hasError && (
          <p
            id={`${inputId}-error`}
            role="alert"
            className="text-xs text-error-500 dark:text-error-400"
          >
            {error}
          </p>
        )}
      </div>
    )
  },
)

Input.displayName = 'Input'

export default Input
