import { NavLink } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'
import { Role, canAccessNavItem } from '@/types/permissions'
import { cn } from '@/utils/cn'

import { NAV_ICON_BY_PATH, NavIcon } from './NavIcons'
import SidebarFooter from './SidebarFooter'

export interface NavItem {
  label: string
  path: string
  roles?: Role[]
}

export const WORKSPACE_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Chat', path: '/chat' },
  { label: 'Documents', path: '/documents' },
]

export const MANAGE_NAV_ITEMS: NavItem[] = [
  { label: 'Admin Portal', path: '/admin', roles: [Role.Admin] },
  { label: 'Users', path: '/admin/users', roles: [Role.Admin] },
  { label: 'Monitoring', path: '/monitoring', roles: [Role.Admin] },
  { label: 'Profile', path: '/profile' },
]

export const MAIN_NAV_ITEMS: NavItem[] = [...WORKSPACE_NAV_ITEMS, ...MANAGE_NAV_ITEMS]

export interface NavGroup {
  id: 'workspace' | 'manage'
  label: string
  items: NavItem[]
}

export const NAV_GROUPS: NavGroup[] = [
  { id: 'workspace', label: 'Workspace', items: WORKSPACE_NAV_ITEMS },
  { id: 'manage', label: 'Manage', items: MANAGE_NAV_ITEMS },
]

export interface SidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  width: number
  onCloseMobile: () => void
}

function NavSection({
  group,
  collapsed,
  visibleItems,
  onCloseMobile,
  showDivider,
}: {
  group: NavGroup
  collapsed: boolean
  visibleItems: NavItem[]
  onCloseMobile: () => void
  showDivider: boolean
}) {
  if (visibleItems.length === 0) return null

  return (
    <div className={cn(showDivider && 'mt-6 border-t border-border-subtle pt-6')}>
      {!collapsed && (
        <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-[0.06em] text-subtle">
          {group.label}
        </p>
      )}
      <ul className="flex flex-col gap-1">
        {visibleItems.map((item) => {
          const iconName = NAV_ICON_BY_PATH[item.path] ?? 'dashboard'
          return (
            <li key={item.path}>
              <NavLink
                to={item.path}
                title={collapsed ? item.label : undefined}
                data-roles={item.roles?.join(',') ?? undefined}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  cn(
                    'sidebar-nav-link flex items-center text-sm font-medium transition-all duration-200 ease-out',
                    'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                    collapsed ? 'justify-center rounded-md px-2 py-2.5' : 'gap-3 rounded-md px-3 py-2.5',
                    isActive
                      ? 'sidebar-nav-link--active bg-accent-muted font-semibold text-[#4F46E5] [&_svg]:text-[#4F46E5]'
                      : 'text-muted hover:bg-overlay [&_svg]:text-muted',
                  )
                }
              >
                <NavIcon name={iconName} />
                {!collapsed && <span>{item.label}</span>}
                {collapsed && <span className="sr-only">{item.label}</span>}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default function Sidebar({
  collapsed,
  mobileOpen: _mobileOpen,
  width,
  onCloseMobile,
}: SidebarProps) {
  const { user } = useAuth()

  const visibleGroups = NAV_GROUPS.map((group) => ({
    group,
    items: group.items.filter((item) => canAccessNavItem(user, item.roles)),
  })).filter((entry) => entry.items.length > 0)

  return (
    <aside
      aria-label="Main navigation"
      className={cn(
        'hidden shrink-0 flex-col bg-sidebar md:flex',
        'border-r border-border-subtle',
        'transition-[width] duration-200 ease-in-out',
      )}
      style={{ width }}
    >
      <div
        className={cn(
          'flex h-14 shrink-0 items-center border-b border-border-subtle',
          collapsed ? 'justify-center px-2' : 'px-4',
        )}
      >
        <span
          className={cn(
            'font-display font-semibold text-accent',
            collapsed ? 'text-xs' : 'text-sm',
          )}
          aria-hidden={collapsed}
        >
          {collapsed ? 'K' : 'Knowra'}
        </span>
      </div>

      <nav className="scrollbar-thin flex flex-1 flex-col overflow-y-auto p-2">
        {visibleGroups.map((entry, index) => (
          <NavSection
            key={entry.group.id}
            group={entry.group}
            collapsed={collapsed}
            visibleItems={entry.items}
            onCloseMobile={onCloseMobile}
            showDivider={index > 0}
          />
        ))}
      </nav>

      <SidebarFooter collapsed={collapsed} />
    </aside>
  )
}
