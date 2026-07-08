export interface AdminNavItem {
  label: string
  path: string
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { label: 'Dashboard', path: '/admin' },
  { label: 'Documents', path: '/admin/documents' },
  { label: 'Uploads', path: '/admin/uploads' },
  { label: 'Users', path: '/admin/users' },
  { label: 'Collections', path: '/admin/collections' },
  { label: 'User Analytics', path: '/admin/analytics' },
  { label: 'AI Analytics', path: '/admin/analytics/ai' },
  { label: 'Knowledge Analytics', path: '/admin/analytics/knowledge' },
  { label: 'System Monitoring', path: '/admin/analytics/monitoring' },
  { label: 'Error Analytics', path: '/admin/analytics/errors' },
  { label: 'Reports', path: '/admin/reports' },
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
