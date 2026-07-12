import { NavLink } from 'react-router-dom'

import {
  ADMIN_DASHBOARD_ITEM,
  ADMIN_NAV_GROUPS,
  type AdminNavGroup,
  type AdminNavItem,
} from '@/features/admin/constants/navigation'
import { cn } from '@/utils/cn'

import { ADMIN_NAV_ICON_BY_PATH, AdminNavIcon } from './AdminNavIcons'

export interface AdminSidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onCloseMobile: () => void
}

function AdminNavLink({
  item,
  collapsed,
  onCloseMobile,
}: {
  item: AdminNavItem
  collapsed: boolean
  onCloseMobile: () => void
}) {
  const iconName = ADMIN_NAV_ICON_BY_PATH[item.path] ?? 'dashboard'

  return (
    <li className="nav-item">
      <NavLink
        to={item.path}
        end={item.path === '/admin'}
        aria-label={collapsed ? item.label : undefined}
        onClick={onCloseMobile}
        className={({ isActive }) =>
          cn(
            'flex items-center rounded-md text-sm font-medium transition-colors duration-200',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
            collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
            isActive && 'active bg-accent-muted text-accent',
            isActive ? '[&_.nav-icon]:text-accent' : 'text-muted hover:bg-overlay hover:text-foreground',
          )
        }
      >
        <AdminNavIcon name={iconName} />
        {!collapsed && <span>{item.label}</span>}
        {collapsed && (
          <span className="nav-tooltip" aria-hidden="true">
            {item.label}
          </span>
        )}
      </NavLink>
    </li>
  )
}

function AdminNavSection({
  group,
  collapsed,
  onCloseMobile,
  showDivider,
}: {
  group: AdminNavGroup
  collapsed: boolean
  onCloseMobile: () => void
  showDivider: boolean
}) {
  return (
    <div className={cn(showDivider && 'mt-6 border-t border-border-subtle pt-6')}>
      {!collapsed && (
        <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-[0.06em] text-subtle">
          {group.label}
        </p>
      )}
      <ul className="flex flex-col gap-1">
        {group.items.map((item) => (
          <AdminNavLink
            key={item.path}
            item={item}
            collapsed={collapsed}
            onCloseMobile={onCloseMobile}
          />
        ))}
      </ul>
    </div>
  )
}

export default function AdminSidebar({
  collapsed,
  mobileOpen,
  onCloseMobile,
}: AdminSidebarProps) {
  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close admin navigation menu"
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        aria-label="Admin navigation"
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col bg-sidebar',
          'border-r border-border-subtle transition-all duration-200 ease-in-out',
          collapsed ? 'w-16' : 'w-60',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          'lg:static lg:translate-x-0 lg:shrink-0',
        )}
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
            {collapsed ? 'Admin' : 'Admin Portal'}
          </span>
        </div>

        <nav
          className="flex flex-1 flex-col overflow-y-auto p-2 scrollbar-thin"
          aria-label="Admin sections"
        >
          <ul className="flex flex-col gap-1">
            <AdminNavLink
              item={ADMIN_DASHBOARD_ITEM}
              collapsed={collapsed}
              onCloseMobile={onCloseMobile}
            />
          </ul>

          {ADMIN_NAV_GROUPS.map((group, index) => (
            <AdminNavSection
              key={group.id}
              group={group}
              collapsed={collapsed}
              onCloseMobile={onCloseMobile}
              showDivider={index === 0 || !collapsed}
            />
          ))}
        </nav>
      </aside>
    </>
  )
}
