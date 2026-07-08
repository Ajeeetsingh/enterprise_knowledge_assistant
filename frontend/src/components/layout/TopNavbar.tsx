import Button from '@/components/ui/Button'
import UserMenu from '@/components/layout/UserMenu'
import { useTheme } from '@/contexts/ThemeContext'
import { cn } from '@/utils/cn'

export interface TopNavbarProps {
  sidebarCollapsed: boolean
  onToggleSidebar: () => void
  onOpenMobileMenu: () => void
}

export default function TopNavbar({
  sidebarCollapsed,
  onToggleSidebar,
  onOpenMobileMenu,
}: TopNavbarProps) {
  const { theme, toggleTheme } = useTheme()

  return (
    <header
      className={cn(
        'flex h-14 shrink-0 items-center justify-between gap-4',
        'border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900',
        'sm:px-6',
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        {/* Mobile menu toggle */}
        <Button
          variant="ghost"
          size="sm"
          className="lg:hidden"
          aria-label="Open navigation menu"
          onClick={onOpenMobileMenu}
        >
          Menu
        </Button>

        {/* Desktop sidebar collapse toggle */}
        <Button
          variant="ghost"
          size="sm"
          className="hidden lg:inline-flex"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!sidebarCollapsed}
          onClick={onToggleSidebar}
        >
          {sidebarCollapsed ? '»' : '«'}
        </Button>

        <h1 className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-50 sm:text-base">
          Enterprise Knowledge Assistant
        </h1>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <Button
          variant="ghost"
          size="sm"
          aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
          onClick={toggleTheme}
        >
          {theme === 'light' ? 'Dark' : 'Light'}
        </Button>

        <UserMenu />
      </div>
    </header>
  )
}
