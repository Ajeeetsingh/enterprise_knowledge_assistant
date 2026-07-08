import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Badge from '@/components/ui/Badge'
import { useAuth } from '@/contexts/AuthContext'
import { getUserInitials, getUserRoleLabel } from '@/utils/userDisplay'
import { cn } from '@/utils/cn'

const MENU_ITEM_SELECTOR = '[role="menuitem"]'

export default function UserMenu() {
  const menuId = useId()
  const containerRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const displayName = user?.full_name ?? 'User'
  const displayEmail = user?.email ?? ''
  const roleLabel = getUserRoleLabel(user?.roles ?? [], user?.is_superuser ?? false)
  const initials = getUserInitials(displayName)

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        return
      }

      if (!menuRef.current) return

      const items = Array.from(
        menuRef.current.querySelectorAll<HTMLButtonElement>(MENU_ITEM_SELECTOR),
      ).filter((item) => !item.disabled)

      if (items.length === 0) return

      const activeIndex = items.findIndex((item) => item === document.activeElement)

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        const next = activeIndex < 0 ? 0 : (activeIndex + 1) % items.length
        items[next]?.focus()
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        const next =
          activeIndex < 0 ? items.length - 1 : (activeIndex - 1 + items.length) % items.length
        items[next]?.focus()
      }

      if (event.key === 'Home') {
        event.preventDefault()
        items[0]?.focus()
      }

      if (event.key === 'End') {
        event.preventDefault()
        items[items.length - 1]?.focus()
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    const firstItem = menuRef.current?.querySelector<HTMLButtonElement>(MENU_ITEM_SELECTOR)
    firstItem?.focus()

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  async function handleLogout() {
    setOpen(false)
    try {
      await logout()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  function handleProfile() {
    setOpen(false)
    navigate('/profile')
  }

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`User menu for ${displayName}`}
        className={cn(
          'flex items-center gap-2 rounded-md border border-neutral-200 px-2 py-1.5 sm:px-3',
          'text-left transition-colors',
          'hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          'dark:border-neutral-700 dark:hover:bg-neutral-800 dark:focus-visible:ring-offset-neutral-900',
          open && 'bg-neutral-50 dark:bg-neutral-800',
        )}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span
          aria-hidden
          className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
        >
          {initials}
        </span>
        <span className="hidden min-w-0 flex-col sm:flex">
          <span className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-50">
            {displayName}
          </span>
          <span className="truncate text-xs text-neutral-500 dark:text-neutral-400">
            {displayEmail}
          </span>
        </span>
      </button>

      {open && (
        <div
          id={menuId}
          ref={menuRef}
          role="menu"
          aria-label="User account menu"
          className={cn(
            'absolute right-0 top-full z-50 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-md border border-neutral-200 bg-white py-1 shadow-lg',
            'dark:border-neutral-700 dark:bg-neutral-900',
          )}
        >
          <div className="border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
            <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              {displayName}
            </p>
            <p className="mt-0.5 truncate text-xs text-neutral-500 dark:text-neutral-400">
              {displayEmail}
            </p>
            <div className="mt-2">
              <Badge variant="info">{roleLabel}</Badge>
            </div>
          </div>

          <button
            type="button"
            role="menuitem"
            className="block w-full px-4 py-2.5 text-left text-sm text-neutral-700 hover:bg-neutral-100 focus-visible:bg-neutral-100 focus-visible:outline-none dark:text-neutral-200 dark:hover:bg-neutral-800"
            onClick={handleProfile}
          >
            My Profile
          </button>

          <button
            type="button"
            role="menuitem"
            className="block w-full px-4 py-2.5 text-left text-sm text-error-700 hover:bg-error-50 focus-visible:bg-error-50 focus-visible:outline-none dark:text-error-400 dark:hover:bg-error-700/10"
            onClick={() => void handleLogout()}
          >
            Logout
          </button>
        </div>
      )}
    </div>
  )
}
