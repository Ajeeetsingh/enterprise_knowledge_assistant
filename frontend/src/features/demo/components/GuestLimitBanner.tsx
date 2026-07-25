import GuestAuthLink from './GuestAuthLink'
import { cn } from '@/utils/cn'

export default function GuestLimitBanner() {
  return (
    <div
      className={cn(
        'mx-4 mb-3 rounded-[var(--radius-lg)] border border-border-subtle',
        'bg-surface-raised px-4 py-4 shadow-elevation-sm sm:mx-6',
      )}
      role="status"
    >
      <p className="text-sm font-semibold text-foreground">
        You&apos;ve reached the guest demo limit
      </p>
      <p className="mt-1 text-sm text-muted">
        Sign in to continue exploring Knowra with your workspace.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <GuestAuthLink
          className={cn(
            'inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white',
            'transition-colors hover:bg-accent-hover',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          Sign In
        </GuestAuthLink>
        <GuestAuthLink
          to="/register"
          className={cn(
            'inline-flex items-center rounded-md border border-border-default px-3 py-1.5',
            'text-sm font-medium text-foreground transition-colors hover:bg-overlay',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          Create Account
        </GuestAuthLink>
      </div>
    </div>
  )
}
