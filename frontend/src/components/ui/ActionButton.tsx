import { forwardRef, type ButtonHTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

export interface ActionButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  destructive?: boolean
}

const ActionButton = forwardRef<HTMLButtonElement, ActionButtonProps>(
  ({ destructive = false, className, children, type = 'button', ...props }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          'action-button',
          destructive && 'action-button--destructive',
          className,
        )}
        {...props}
      >
        {children}
      </button>
    )
  },
)

ActionButton.displayName = 'ActionButton'

export default ActionButton
