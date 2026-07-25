import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

const focusRing =
  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]'

export default function LandingFooter() {
  const year = new Date().getFullYear()
  const { isAuthenticated, isLoading } = useAuth()
  const showDashboard = !isLoading && isAuthenticated

  return (
    <footer className="border-t border-border-subtle px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-md">
          <Link
            to="/"
            className={cn('inline-flex items-center gap-2.5 rounded-md text-foreground', focusRing)}
          >
            <img src="/favicon.svg" alt="" width={24} height={23} className="size-6" />
            <span className="text-sm font-semibold tracking-tight">
              Knowra
            </span>
          </Link>
          <p className="mt-3 text-xs leading-relaxed text-subtle">
            Powered by hybrid retrieval, semantic search, reranking, and RAG.
          </p>
        </div>

        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {showDashboard ? (
            <Link
              to="/dashboard"
              className={cn('text-muted transition-colors hover:text-foreground', focusRing)}
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/demo"
                className={cn('text-muted transition-colors hover:text-foreground', focusRing)}
              >
                Try the Demo
              </Link>
              <Link
                to="/login"
                className={cn('text-muted transition-colors hover:text-foreground', focusRing)}
              >
                Sign In
              </Link>
            </>
          )}
        </nav>
      </div>

      <div className="mx-auto mt-8 max-w-6xl border-t border-border-subtle pt-6">
        <p className="text-xs text-subtle">
          © {year} Knowra. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
