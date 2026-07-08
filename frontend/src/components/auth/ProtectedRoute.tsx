import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/contexts/AuthContext'

import AuthLoading from './AuthLoading'

export interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * Renders children only when the user is authenticated.
 * Shows a loading state during session bootstrap; redirects to /login otherwise.
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <AuthLoading message="Checking your session…" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
