import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { Badge, Button, Card } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import * as authStorage from '@/services/authStorage'
import { Permission, Role, getUserPermissions, hasPermission, hasRole } from '@/types/permissions'

function TokenStatus({ label, present }: { label: string; present: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-neutral-600 dark:text-neutral-400">{label}</span>
      <Badge variant={present ? 'success' : 'error'}>
        {present ? 'Present' : 'Missing'}
      </Badge>
    </div>
  )
}

function maskToken(token: string | null): string {
  if (!token) return '—'
  if (token.length <= 12) return '••••••••'
  return `${token.slice(0, 6)}…${token.slice(-4)}`
}

export default function AuthDebugPage() {
  const { user, isAuthenticated, isLoading, logout, refreshUser } = useAuth()
  const location = useLocation()
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionPending, setActionPending] = useState(false)

  const accessToken = authStorage.getAccessToken()
  const refreshToken = authStorage.getRefreshToken()

  const protectedRouteWouldAllow = !isLoading && isAuthenticated
  const publicRouteWouldAllow = !isLoading && !isAuthenticated
  const userPermissions = getUserPermissions(user)

  async function handleRefreshUser() {
    setActionError(null)
    setActionPending(true)
    try {
      await refreshUser()
    } catch {
      setActionError('Failed to refresh user profile.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleLogout() {
    setActionError(null)
    setActionPending(true)
    try {
      await logout()
    } catch {
      setActionError('Logout request failed, but local session was cleared.')
    } finally {
      setActionPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Auth Debug
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Manual verification for authentication infrastructure. Login UI is not
          implemented yet — obtain tokens via the backend API and store them in
          localStorage to test session restoration.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Session status">
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-neutral-600 dark:text-neutral-400">Loading</dt>
              <dd>
                <Badge variant={isLoading ? 'warning' : 'info'}>
                  {isLoading ? 'Yes' : 'No'}
                </Badge>
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-neutral-600 dark:text-neutral-400">Authenticated</dt>
              <dd>
                <Badge variant={isAuthenticated ? 'success' : 'error'}>
                  {isAuthenticated ? 'Yes' : 'No'}
                </Badge>
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="Stored tokens">
          <div className="space-y-3">
            <TokenStatus label="Access token" present={accessToken !== null} />
            <TokenStatus label="Refresh token" present={refreshToken !== null} />
            <div className="space-y-1 border-t border-neutral-200 pt-3 text-xs text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
              <p>Access: {maskToken(accessToken)}</p>
              <p>Refresh: {maskToken(refreshToken)}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Route protection">
        <dl className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-600 dark:text-neutral-400">Current path</dt>
            <dd>
              <code className="text-xs">{location.pathname}</code>
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-600 dark:text-neutral-400">ProtectedRoute access</dt>
            <dd>
              <Badge variant={protectedRouteWouldAllow ? 'success' : 'error'}>
                {protectedRouteWouldAllow ? 'Allowed' : 'Denied → /login'}
              </Badge>
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-600 dark:text-neutral-400">PublicRoute (/login) access</dt>
            <dd>
              <Badge variant={publicRouteWouldAllow ? 'success' : 'error'}>
                {publicRouteWouldAllow ? 'Allowed' : 'Denied → /dashboard'}
              </Badge>
            </dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          <Link to="/login" className="text-primary-600 hover:underline dark:text-primary-400">
            Test /login
          </Link>
          <Link to="/dashboard" className="text-primary-600 hover:underline dark:text-primary-400">
            Test /dashboard
          </Link>
          <Link
            to="/unauthorized"
            className="text-primary-600 hover:underline dark:text-primary-400"
          >
            Test /unauthorized
          </Link>
        </div>
      </Card>

      <Card title="Authorization utilities (preview)">
        <dl className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-600 dark:text-neutral-400">hasRole(Admin)</dt>
            <dd>
              <Badge variant={hasRole(user, Role.Admin) ? 'success' : 'info'}>
                {hasRole(user, Role.Admin) ? 'Yes' : 'No'}
              </Badge>
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-neutral-600 dark:text-neutral-400">hasPermission(AuditView)</dt>
            <dd>
              <Badge variant={hasPermission(user, Permission.AuditView) ? 'success' : 'info'}>
                {hasPermission(user, Permission.AuditView) ? 'Yes' : 'No'}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-neutral-600 dark:text-neutral-400">Granted permissions</dt>
            <dd className="mt-2">
              {userPermissions.length > 0 ? (
                <ul className="list-inside list-disc text-xs text-neutral-700 dark:text-neutral-300">
                  {userPermissions.map((permission) => (
                    <li key={permission}>{permission}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-neutral-500 dark:text-neutral-400">None</p>
              )}
            </dd>
          </div>
        </dl>
      </Card>

      <Card title="Current user">
        {user ? (
          <pre className="overflow-x-auto rounded-md bg-neutral-100 p-4 text-xs text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
            {JSON.stringify(user, null, 2)}
          </pre>
        ) : (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            No authenticated user. Store tokens in localStorage and reload, or call{' '}
            <code className="text-xs">login()</code> programmatically once a login form
            exists.
          </p>
        )}
      </Card>

      <Card title="Actions">
        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            disabled={actionPending || isLoading}
            onClick={() => void handleRefreshUser()}
          >
            Refresh User
          </Button>
          <Button
            variant="danger"
            disabled={actionPending || isLoading}
            onClick={() => void handleLogout()}
          >
            Logout
          </Button>
        </div>
        {actionError && (
          <p role="alert" className="mt-3 text-sm text-error-500">
            {actionError}
          </p>
        )}
      </Card>

      <Card title="Manual login (curl)">
        <pre className="overflow-x-auto rounded-md bg-neutral-100 p-4 text-xs text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
{`curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"admin@example.com","password":"your-password"}'`}
        </pre>
        <p className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">
          Copy <code>access_token</code> and <code>refresh_token</code> from the response
          into localStorage keys <code>eka_access_token</code> and{' '}
          <code>eka_refresh_token</code>, then reload this page.
        </p>
      </Card>
    </div>
  )
}
