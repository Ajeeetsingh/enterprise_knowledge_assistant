import { Link } from 'react-router-dom'

import { MoonIcon, SunIcon } from '@/components/layout/NavIcons'
import { useTheme } from '@/contexts/ThemeContext'
import { cn } from '@/utils/cn'

import GuestAuthLink from './GuestAuthLink'
import GuestChatPanel from './GuestChatPanel'
import GuestChatSidebar from './GuestChatSidebar'

/**
 * Lightweight public shell for /demo — visually similar to the product chat,
 * without AppLayout authenticated navigation (Admin, Documents, Profile, etc.).
 */
export default function GuestDemoShell() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-canvas">
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border-subtle bg-surface px-4 sm:px-6">
        <Link
          to="/"
          className={cn(
            'flex min-w-0 items-center gap-2.5 rounded-md text-foreground',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          <img src="/favicon.svg" alt="" width={28} height={27} className="size-7 shrink-0" />
          <span className="truncate text-sm font-semibold tracking-tight">
            Knowra
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <p className="hidden text-xs text-muted sm:block" role="status">
            Guest session
          </p>
          <button
            type="button"
            onClick={toggleTheme}
            className={cn(
              'inline-flex size-9 items-center justify-center rounded-md text-muted',
              'transition-colors hover:bg-overlay hover:text-foreground',
              'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
            )}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon className="size-5" /> : <MoonIcon className="size-5" />}
          </button>
          <GuestAuthLink
            className={cn(
              'inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white',
              'transition-colors hover:bg-accent-hover',
              'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
            )}
          >
            Sign In
          </GuestAuthLink>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="hidden w-64 shrink-0 md:block lg:w-72">
          <GuestChatSidebar />
        </div>
        <GuestChatPanel />
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border-subtle px-4 py-2 md:hidden">
        <p className="text-xs text-muted">Guest session</p>
        <GuestAuthLink className="text-sm font-medium text-accent hover:text-accent-hover">
          Sign in
        </GuestAuthLink>
      </div>
    </div>
  )
}
