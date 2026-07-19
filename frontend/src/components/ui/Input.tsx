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
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-muted">
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
            'block w-full rounded-[var(--radius-sm)] border px-3 py-2.5 text-sm',
            'bg-surface text-foreground placeholder:text-subtle',
            'transition-[border-color,box-shadow] duration-150 ease-out',
            'focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-50',
            hasError
              ? 'border-error-500 focus:border-error-500 focus:shadow-[0_0_0_3px_var(--status-bad-muted)]'
              : 'border-border-default focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-muted)]',
            className,
          )}
          {...props}
        />

        {hint && !hasError && (
          <p id={`${inputId}-hint`} className="text-xs text-subtle">
            {hint}
          </p>
        )}

        {hasError && (
          <p id={`${inputId}-error`} role="alert" className="text-xs text-status-bad">
            {error}
          </p>
        )}
      </div>
    )
  },
)

Input.displayName = 'Input'

export default Input
