import { useLocation } from 'react-router-dom'

import Button from '@/components/ui/Button'
import UserMenu from '@/components/layout/UserMenu'
import {
  ConversationsIcon,
  HamburgerIcon,
  MoonIcon,
  SunIcon,
} from '@/components/layout/NavIcons'
import { conversationDisplayTitle } from '@/features/chat/types'
import { useLayoutContext } from '@/contexts/LayoutContext'
import { useTheme } from '@/contexts/ThemeContext'
import { useMinWidthMediaQuery } from '@/hooks/useMinWidthMediaQuery'
import { DESKTOP_MIN, LAYOUT_BREAKPOINTS } from '@/utils/layoutStorage'
import { cn } from '@/utils/cn'

export interface TopNavbarProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
}

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/chat': 'Chat',
  '/documents': 'Documents',
  '/admin': 'Admin Portal',
  '/admin/users': 'Users',
  '/users': 'Users',
  '/monitoring': 'Monitoring',
  '/profile': 'Profile',
}

function formatRouteLabel(pathname: string): string {
  if (ROUTE_LABELS[pathname]) return ROUTE_LABELS[pathname]

  const segment = pathname.split('/').filter(Boolean).at(-1)
  if (!segment) return 'Home'

  return segment
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function HeaderStatus({ label }: { label: string }) {
  return (
    <div
      className="hidden items-center gap-2 text-xs text-muted md:flex"
      role="status"
      aria-live="polite"
    >
      <span className="relative flex size-2">
        <span className="status-dot absolute inline-flex size-full rounded-full bg-success-500 opacity-75" />
        <span className="relative inline-flex size-2 rounded-full bg-success-500" />
      </span>
      <span>{label}</span>
    </div>
  )
}

export default function TopNavbar({
  sidebarCollapsed,
  onToggleSidebar,
}: TopNavbarProps) {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const {
    isChatRoute,
    openConversationDrawer,
    openMobileShell,
    mobileChatPanel,
  } = useLayoutContext()
  const isAtLeastMobile = useMinWidthMediaQuery(LAYOUT_BREAKPOINTS.mobile)
  const isAtLeastDesktop = useMinWidthMediaQuery(DESKTOP_MIN)
  const isMobile = !isAtLeastMobile
  const isTablet = isAtLeastMobile && !isAtLeastDesktop

  const activeConversation = mobileChatPanel?.selectedId
    ? mobileChatPanel.conversations.find(
        (conversation) => conversation.id === mobileChatPanel.selectedId,
      )
    : null

  const breadcrumbParent = isChatRoute && activeConversation ? 'Chat' : null
  const breadcrumbCurrent = isChatRoute
    ? activeConversation
      ? conversationDisplayTitle(activeConversation)
      : 'Chat'
    : formatRouteLabel(location.pathname)

  const statusLabel = isChatRoute
    ? 'Connected to Knowledge Base'
    : 'AI assistant ready'

  return (
    <header
      className={cn(
        'surface-header sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-3 px-5',
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
        {isMobile ? (
          <Button
            variant="ghost"
            size="sm"
            className="size-9 shrink-0 px-0 text-muted hover:bg-overlay hover:text-foreground"
            aria-label="Open menu"
            onClick={openMobileShell}
          >
            <HamburgerIcon />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="hidden size-9 shrink-0 px-0 text-muted hover:bg-overlay hover:text-foreground md:inline-flex"
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!sidebarCollapsed}
            onClick={onToggleSidebar}
          >
            <HamburgerIcon />
          </Button>
        )}

        {isChatRoute && (isMobile || isTablet) && (
          <Button
            variant="ghost"
            size="sm"
            className="size-9 shrink-0 px-0 text-muted hover:bg-overlay hover:text-foreground lg:hidden"
            aria-label="Open conversations"
            onClick={openConversationDrawer}
          >
            <ConversationsIcon />
          </Button>
        )}

        <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2">
          <div className="min-w-0 truncate text-[13px]">
            {breadcrumbParent ? (
              <>
                <span className="text-muted">{breadcrumbParent}</span>
                <span className="mx-1.5 text-subtle" aria-hidden>
                  /
                </span>
                <span className="font-medium text-foreground">{breadcrumbCurrent}</span>
              </>
            ) : (
              <span className="font-medium text-foreground">{breadcrumbCurrent}</span>
            )}
          </div>
          <HeaderStatus label={statusLabel} />
        </nav>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="size-9 px-0 text-muted hover:bg-overlay hover:text-foreground"
          aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
          onClick={toggleTheme}
        >
          {theme === 'light' ? <MoonIcon /> : <SunIcon />}
        </Button>

        <UserMenu compact />
      </div>
    </header>
  )
}
