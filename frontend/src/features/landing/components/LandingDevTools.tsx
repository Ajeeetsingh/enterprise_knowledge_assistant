import { useEffect, useId, useState } from 'react'
import { Link } from 'react-router-dom'

import { cn } from '@/utils/cn'

const DEV_LINKS = [
  { to: '/design-system', label: 'Design system' },
  { to: '/layout-preview', label: 'Layout preview' },
  { to: '/auth-debug', label: 'Auth debug' },
  { to: '/notifications-demo', label: 'Notifications demo' },
] as const

/**
 * Discreet developer-tools control. Only mounted when import.meta.env.DEV.
 * Must never appear in production builds.
 */
export default function LandingDevTools() {
  const panelId = useId()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  return (
    <div className="relative">
      <button
        type="button"
        className={cn(
          'rounded-md border border-dashed border-border-default px-2 py-1',
          'text-[11px] font-medium uppercase tracking-wide text-subtle',
          'transition-colors hover:border-border-default hover:text-muted',
          'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
        )}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        Dev tools
      </button>

      {open && (
        <div
          id={panelId}
          role="menu"
          aria-label="Development tools"
          className={cn(
            'absolute right-0 z-50 mt-2 w-48 overflow-hidden rounded-md',
            'border border-border-default bg-surface-raised p-1 shadow-elevation-md',
          )}
        >
          {DEV_LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              role="menuitem"
              className={cn(
                'block rounded-sm px-3 py-2 text-sm text-muted',
                'transition-colors hover:bg-overlay hover:text-foreground',
                'focus-visible:outline-none focus-visible:bg-overlay focus-visible:text-foreground',
              )}
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
