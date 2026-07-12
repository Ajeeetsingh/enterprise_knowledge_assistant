import { createBrowserRouter } from 'react-router-dom'

import { ProtectedRoute, PublicRoute, AdminRoute } from '@/components/auth'
import {
  AdminCollectionsPage,
  AdminDashboardPage,
  AdminDocumentsPage,
  AdminLayout,
  AdminUploadsPage,
  AdminUsersPage,
} from '@/features/admin'
import { AIAnalyticsPage, ErrorAnalyticsPage, KnowledgeAnalyticsPage, SystemMonitoringPage, UserAnalyticsPage } from '@/features/analytics'
import DocumentViewerPage from '@/features/document-viewer/pages/DocumentViewerPage'
import { ReportsPage } from '@/features/reports'
import AppLayout from '@/layouts/AppLayout'
import AuthLayout from '@/layouts/AuthLayout'
import RootLayout from '@/layouts/RootLayout'
import AuthDebugPage from '@/pages/AuthDebugPage'
import ChatPage from '@/pages/ChatPage'
import DashboardPage from '@/pages/DashboardPage'
import DocumentsPage from '@/pages/DocumentsPage'
import DesignSystemPage from '@/pages/DesignSystemPage'
import HomePage from '@/pages/HomePage'
import LayoutPreviewPage from '@/pages/LayoutPreviewPage'
import ProfilePage from '@/pages/ProfilePage'
import LoginPage from '@/pages/LoginPage'
import MonitoringPage from '@/pages/MonitoringPage'
import NotFoundPage from '@/pages/NotFoundPage'
import NotificationsDemoPage from '@/pages/NotificationsDemoPage'
import UnauthorizedPage from '@/pages/UnauthorizedPage'
import UsersPage from '@/pages/UsersPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'design-system', element: <DesignSystemPage /> },
      {
        element: <AuthLayout />,
        children: [
          {
            path: 'login',
            element: (
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            ),
          },
        ],
      },
      {
        element: (
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        ),
        children: [
          { path: 'dashboard', element: <DashboardPage /> },
          { path: 'chat', element: <ChatPage /> },
          { path: 'documents/:documentId', element: <DocumentViewerPage /> },
          { path: 'documents', element: <DocumentsPage /> },
          { path: 'profile', element: <ProfilePage /> },
          {
            path: 'users',
            element: (
              <AdminRoute>
                <UsersPage />
              </AdminRoute>
            ),
          },
          {
            path: 'monitoring',
            element: (
              <AdminRoute>
                <MonitoringPage />
              </AdminRoute>
            ),
          },
          { path: 'layout-preview', element: <LayoutPreviewPage /> },
          { path: 'auth-debug', element: <AuthDebugPage /> },
          { path: 'notifications-demo', element: <NotificationsDemoPage /> },
          { path: 'unauthorized', element: <UnauthorizedPage /> },
        ],
      },
      {
        path: 'admin',
        element: (
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        ),
        children: [
          { index: true, element: <AdminDashboardPage /> },
          { path: 'documents', element: <AdminDocumentsPage /> },
          { path: 'uploads', element: <AdminUploadsPage /> },
          { path: 'users', element: <AdminUsersPage /> },
          { path: 'collections', element: <AdminCollectionsPage /> },
          { path: 'analytics', element: <UserAnalyticsPage /> },
          { path: 'analytics/ai', element: <AIAnalyticsPage /> },
          { path: 'analytics/knowledge', element: <KnowledgeAnalyticsPage /> },
          { path: 'analytics/monitoring', element: <SystemMonitoringPage /> },
          { path: 'analytics/errors', element: <ErrorAnalyticsPage /> },
          { path: 'reports', element: <ReportsPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default router
