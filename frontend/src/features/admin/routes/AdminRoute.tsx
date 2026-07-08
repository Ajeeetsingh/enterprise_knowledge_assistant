import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import AuthLoading from '@/components/auth/AuthLoading'
import { useAuth } from '@/contexts/AuthContext'
import { isAdminUser } from '@/types/permissions'

export interface AdminRouteProps {
  children: ReactNode
}

/**
 * Admin-only route guard using existing RBAC ({@link isAdminUser}).
 * Unauthenticated users are redirected to login; non-admins to /unauthorized.
 */
export default function AdminRoute({ children }: AdminRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <AuthLoading message="Checking your permissions…" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (!isAdminUser(user)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children
}
