import { useLocation, useNavigate } from 'react-router-dom'

import Button from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'
import { getAdminPageTitle } from '@/features/admin/constants/navigation'
import { getUserInitials } from '@/utils/userDisplay'
import { cn } from '@/utils/cn'

export interface AdminHeaderProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
  onOpenMobileMenu: () => void
}

export default function AdminHeader({
  sidebarCollapsed,
  onToggleSidebar,
  onOpenMobileMenu,
}: AdminHeaderProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const pageTitle = getAdminPageTitle(pathname)

  async function handleLogout() {
    try {
      await logout()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <header
      className={cn(
        'flex h-14 shrink-0 items-center justify-between gap-4',
        'border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900',
        'sm:px-6',
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          className="lg:hidden"
          aria-label="Open admin navigation menu"
          onClick={onOpenMobileMenu}
        >
          Menu
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="hidden lg:inline-flex"
          aria-label={sidebarCollapsed ? 'Expand admin sidebar' : 'Collapse admin sidebar'}
          aria-expanded={!sidebarCollapsed}
          onClick={onToggleSidebar}
        >
          {sidebarCollapsed ? '»' : '«'}
        </Button>

        <h1 className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-50 sm:text-base">
          {pageTitle}
        </h1>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <div
          className="hidden min-w-0 flex-col text-right sm:flex"
          aria-label="Signed-in administrator"
        >
          <span className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-50">
            {user?.full_name ?? 'Administrator'}
          </span>
          <span className="truncate text-xs text-neutral-500 dark:text-neutral-400">
            {user?.email ?? ''}
          </span>
        </div>

        <div
          className="flex items-center gap-2 rounded-md border border-neutral-200 px-3 py-1.5 dark:border-neutral-700"
          aria-label="Administrator account"
        >
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
          >
            {getUserInitials(user?.full_name ?? 'Admin')}
          </span>
        </div>

        <Button variant="ghost" size="sm" onClick={() => void handleLogout()}>
          Log out
        </Button>
      </div>
    </header>
  )
}
