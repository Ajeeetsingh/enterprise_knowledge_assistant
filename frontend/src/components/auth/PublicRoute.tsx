import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'

import AuthLoading from './AuthLoading'

export interface PublicRouteProps {
  children: ReactNode
}

/**
 * Renders children only when the user is not authenticated.
 * Redirects authenticated users to /dashboard.
 */
export default function PublicRoute({ children }: PublicRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <AuthLoading message="Checking your session…" />
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
