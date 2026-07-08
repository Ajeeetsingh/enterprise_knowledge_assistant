export { default as AdminRoute } from './routes/AdminRoute'
export type { AdminRouteProps } from './routes/AdminRoute'

export { default as AdminLayout } from './layouts/AdminLayout'

export { default as AdminSidebar } from './components/AdminSidebar'
export type { AdminSidebarProps } from './components/AdminSidebar'

export { default as AdminHeader } from './components/AdminHeader'
export type { AdminHeaderProps } from './components/AdminHeader'

export { default as AdminDashboardPage } from './pages/AdminDashboardPage'
export { default as AdminDocumentsPage } from './pages/AdminDocumentsPage'
export { default as AdminUploadsPage } from './pages/AdminUploadsPage'
export { default as AdminUsersPage } from './pages/AdminUsersPage'
export { default as AdminCollectionsPage } from './pages/AdminCollectionsPage'

export { ADMIN_NAV_ITEMS, ADMIN_PAGE_TITLES, getAdminPageTitle } from './constants/navigation'
export type { AdminNavItem } from './constants/navigation'
