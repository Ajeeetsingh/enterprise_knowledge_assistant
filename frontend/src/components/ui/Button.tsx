import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 ' +
    'focus-visible:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-400',
  secondary:
    'bg-white text-neutral-700 border border-neutral-300 hover:bg-neutral-50 ' +
    'active:bg-neutral-100 focus-visible:ring-neutral-400 ' +
    'dark:bg-neutral-800 dark:text-neutral-200 dark:border-neutral-600 dark:hover:bg-neutral-700',
  danger:
    'bg-error-500 text-white hover:bg-error-700 active:bg-error-700 ' +
    'focus-visible:ring-error-500',
  ghost:
    'bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-200 ' +
    'focus-visible:ring-neutral-400 ' +
    'dark:text-neutral-300 dark:hover:bg-neutral-800',
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
          'transition-colors duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
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
