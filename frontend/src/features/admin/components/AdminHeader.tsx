import { useLocation, useNavigate } from 'react-router-dom'

import Button from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'
import { useSystemMonitoring } from '@/features/analytics/hooks/useSystemMonitoring'
import type { ServiceHealthStatus } from '@/features/analytics/types'
import { getAdminPageTitle } from '@/features/admin/constants/navigation'
import { getUserInitials } from '@/utils/userDisplay'
import { cn } from '@/utils/cn'

export interface AdminHeaderProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
  onOpenMobileMenu: () => void
}

function LogOutIcon() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="size-4"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 12H3m12 0-3-3m3 3-3 3M7 5v14a2 2 0 0 0 2 2h8"
      />
    </svg>
  )
}

function statusLabel(status: ServiceHealthStatus | undefined): string {
  if (status === 'healthy') return 'All systems healthy'
  if (status === 'degraded') return 'Some systems degraded'
  if (status === 'unavailable') return 'System issues detected'
  return 'Checking system status'
}

function statusDotClass(status: ServiceHealthStatus | undefined): string {
  if (status === 'healthy') return 'bg-status-good'
  if (status === 'degraded') return 'bg-status-warn'
  if (status === 'unavailable') return 'bg-status-bad'
  return 'bg-subtle'
}

function AdminHeaderStatus() {
  const { data } = useSystemMonitoring({ range_preset: 'last_7_days' })
  const status = data?.overall_system_status
  const label = statusLabel(status)

  return (
    <div
      className="hidden items-center gap-2 text-xs text-muted md:flex"
      role="status"
      aria-live="polite"
    >
      <span className="relative flex size-2">
        <span
          className={cn(
            'status-dot absolute inline-flex size-full rounded-full opacity-75',
            statusDotClass(status),
          )}
        />
        <span
          className={cn('relative inline-flex size-2 rounded-full', statusDotClass(status))}
        />
      </span>
      <span>{label}</span>
    </div>
  )
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
    <header className="surface-header flex h-14 shrink-0 items-center justify-between gap-4 px-4 sm:px-6">
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

        <div className="min-w-0">
          <p className="truncate text-[13px] text-muted">
            <span className="text-subtle">Admin</span>
            <span className="mx-1.5 text-subtle">/</span>
            <span className="font-medium text-foreground">{pageTitle}</span>
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <AdminHeaderStatus />

        <div
          className="hidden min-w-0 flex-col text-right sm:flex"
          aria-label="Signed-in administrator"
        >
          <span className="truncate text-sm font-medium text-foreground">
            {user?.full_name ?? 'Administrator'}
          </span>
          <span className="truncate text-xs text-muted">{user?.email ?? ''}</span>
        </div>

        <div
          className="flex items-center gap-2 rounded-md border border-border-subtle px-3 py-1.5"
          aria-label="Administrator account"
        >
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-full bg-accent-muted text-xs font-semibold text-accent"
          >
            {getUserInitials(user?.full_name ?? 'Admin')}
          </span>
        </div>

        <button
          type="button"
          className="admin-logout-button"
          onClick={() => void handleLogout()}
        >
          <LogOutIcon />
          <span className="hidden sm:inline">Log out</span>
        </button>
      </div>
    </header>
  )
}
