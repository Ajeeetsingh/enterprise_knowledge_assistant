import { Link } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import LandingDevTools from './LandingDevTools'
import { ctaNavGhostClass, ctaNavPrimaryClass } from './ctaStyles'

const SECTION_LINKS = [
  { href: '#features', label: 'Features' },
  { href: '#how-it-works', label: 'How it works' },
  { href: '#security', label: 'Security' },
] as const

export default function LandingNavbar() {
  const { isAuthenticated, isLoading } = useAuth()
  const showDashboard = !isLoading && isAuthenticated

  return (
    <header className="sticky top-0 z-40 border-b border-white/50 bg-[rgba(255,255,255,0.72)] backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className={cn(
            'group flex min-w-0 items-center gap-2.5 rounded-xl text-[#111827]',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgb(109_40_217_/_0.25)]',
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
            Knowra
          </span>
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-2 sm:gap-3">
          <div className="mr-1 hidden items-center gap-4 lg:flex">
            {SECTION_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className={cn(
                  'text-sm font-medium text-[#4B5563] transition-colors hover:text-[#111827]',
                  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgb(109_40_217_/_0.25)]',
                )}
              >
                {link.label}
              </a>
            ))}
          </div>

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
              <Link to="/demo" className={ctaNavPrimaryClass}>
                Try the Demo
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
