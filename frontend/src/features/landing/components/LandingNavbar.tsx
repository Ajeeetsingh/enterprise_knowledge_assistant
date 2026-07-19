import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import LandingDevTools from './LandingDevTools'
import { ctaNavGhostClass, ctaNavPrimaryClass } from './ctaStyles'

export default function LandingNavbar() {
  const { isAuthenticated, isLoading } = useAuth()
  const showDashboard = !isLoading && isAuthenticated

  return (
    <header className="sticky top-0 z-40 border-b border-border-subtle bg-[color-mix(in_srgb,var(--bg-canvas)_82%,transparent)] backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className={cn(
            'group flex min-w-0 items-center gap-2.5 rounded-md text-foreground',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          <img
            src="/favicon.svg"
            alt=""
            width={28}
            height={27}
            className="size-7 shrink-0"
          />
          <span className="truncate text-sm font-semibold tracking-tight sm:text-[15px]">
            Enterprise Knowledge Assistant
          </span>
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-2 sm:gap-3">
          {import.meta.env.DEV && <LandingDevTools />}

          {showDashboard ? (
            <Link to="/dashboard" className={ctaNavPrimaryClass}>
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className={cn(ctaNavGhostClass, 'hidden sm:inline-flex')}>
                Sign In
              </Link>
              <Link to="/register" className={ctaNavPrimaryClass}>
                Get Started
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
