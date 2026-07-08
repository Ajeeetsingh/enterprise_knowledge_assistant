import { NavLink } from 'react-router-dom'

import { ADMIN_NAV_ITEMS } from '@/features/admin/constants/navigation'
import { cn } from '@/utils/cn'

export interface AdminSidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onCloseMobile: () => void
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
          'fixed inset-y-0 left-0 z-50 flex flex-col',
          'border-r border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900',
          'transition-all duration-200 ease-in-out',
          collapsed ? 'w-16' : 'w-60',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          'lg:static lg:translate-x-0 lg:shrink-0',
        )}
      >
        <div
          className={cn(
            'flex h-14 shrink-0 items-center border-b border-neutral-200 dark:border-neutral-700',
            collapsed ? 'justify-center px-2' : 'px-4',
          )}
        >
          <span
            className={cn(
              'font-semibold text-primary-700 dark:text-primary-400',
              collapsed ? 'text-xs' : 'text-sm',
            )}
            aria-hidden={collapsed}
          >
            {collapsed ? 'Admin' : 'Admin Portal'}
          </span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2" aria-label="Admin sections">
          {ADMIN_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/admin'}
              title={collapsed ? item.label : undefined}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  'flex items-center rounded-md text-sm font-medium transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
                  'dark:focus-visible:ring-offset-neutral-900',
                  collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5',
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-100',
                )
              }
            >
              {collapsed ? (
                <span aria-hidden className="text-xs font-bold uppercase">
                  {item.label.charAt(0)}
                </span>
              ) : (
                item.label
              )}
              {collapsed && <span className="sr-only">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
