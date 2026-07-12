export interface AdminNavItem {
  label: string
  path: string
}

export interface AdminNavGroup {
  id: 'content' | 'people' | 'analytics' | 'system'
  label: string
  items: AdminNavItem[]
}

export const ADMIN_DASHBOARD_ITEM: AdminNavItem = {
  label: 'Dashboard',
  path: '/admin',
}

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: 'content',
    label: 'Content',
    items: [
      { label: 'Documents', path: '/admin/documents' },
      { label: 'Uploads', path: '/admin/uploads' },
      { label: 'Collections', path: '/admin/collections' },
    ],
  },
  {
    id: 'people',
    label: 'People',
    items: [{ label: 'Users', path: '/admin/users' }],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    items: [
      { label: 'User Analytics', path: '/admin/analytics' },
      { label: 'AI Analytics', path: '/admin/analytics/ai' },
      { label: 'Knowledge Analytics', path: '/admin/analytics/knowledge' },
      { label: 'Error Analytics', path: '/admin/analytics/errors' },
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [
      { label: 'System Monitoring', path: '/admin/analytics/monitoring' },
      { label: 'Reports', path: '/admin/reports' },
    ],
  },
]

/** Flat list of all admin nav items (dashboard + grouped items). */
export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  ADMIN_DASHBOARD_ITEM,
  ...ADMIN_NAV_GROUPS.flatMap((group) => group.items),
]

export const ADMIN_PAGE_TITLES: Record<string, string> = {
  '/admin': 'Dashboard',
  '/admin/documents': 'Documents',
  '/admin/uploads': 'Uploads',
  '/admin/users': 'Users',
  '/admin/collections': 'Collections',
  '/admin/analytics': 'User Analytics',
  '/admin/analytics/ai': 'AI Analytics',
  '/admin/analytics/knowledge': 'Knowledge Analytics',
  '/admin/analytics/monitoring': 'System Monitoring',
  '/admin/analytics/errors': 'Error Analytics',
  '/admin/reports': 'Reporting & Export',
}

export function getAdminPageTitle(pathname: string): string {
  return ADMIN_PAGE_TITLES[pathname] ?? 'Admin Portal'
}
