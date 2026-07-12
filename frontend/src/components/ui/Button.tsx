import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}

const focusRing =
  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]'

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-white shadow-elevation-sm hover:bg-accent-hover active:bg-accent-pressed active:scale-[0.97]',
  secondary:
    'border border-border-default bg-surface-raised text-foreground shadow-elevation-sm ' +
    'hover:bg-overlay active:scale-[0.97]',
  danger:
    'bg-error-500 text-white shadow-elevation-sm hover:bg-error-700 active:scale-[0.97]',
  ghost:
    'bg-transparent text-muted hover:bg-overlay hover:text-foreground active:scale-[0.97]',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8  px-3 text-sm  gap-1.5',
  md: 'h-10 px-4 text-sm  gap-2',
  lg: 'h-12 px-6 text-base gap-2',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || isLoading

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-busy={isLoading}
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium',
          'transition-all duration-150 ease-out',
          focusRing,
          'disabled:pointer-events-none disabled:opacity-50',
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {isLoading && (
          <span
            aria-hidden
            className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
        )}
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'

export default Button
