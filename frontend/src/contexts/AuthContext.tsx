import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import queryClient from '@/app/queryClient'
import SessionExpiredListener from '@/components/auth/SessionExpiredListener'
import { registerUnauthorizedHandler } from '@/services/api'
import * as authApi from '@/services/authApi'
import * as authStorage from '@/services/authStorage'
import type { ApiError } from '@/types'
import type { LoginRequest, User } from '@/types/auth'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    authStorage.clearTokens()
    queryClient.clear()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    if (!authStorage.getAccessToken()) {
      setUser(null)
      return
    }

    try {
      const currentUser = await authApi.getCurrentUser()
      setUser(currentUser)
    } catch {
      clearSession()
    }
  }, [clearSession])

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const tokens = await authApi.login(credentials)
      authStorage.setAccessToken(tokens.access_token)
      authStorage.setRefreshToken(tokens.refresh_token)

      try {
        const currentUser = await authApi.getCurrentUser()
        setUser(currentUser)
      } catch (error) {
        clearSession()
        throw error as ApiError
      }
    },
    [clearSession],
  )

  const logout = useCallback(async () => {
    try {
      if (authStorage.getAccessToken()) {
        await authApi.logout()
      }
    } catch {
      // Always clear local session even if the network call fails.
    } finally {
      clearSession()
    }
  }, [clearSession])

  // Startup: restore session from stored access token.
  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      if (!authStorage.getAccessToken()) {
        if (!cancelled) setIsLoading(false)
        return
      }

      try {
        const currentUser = await authApi.getCurrentUser()
        if (!cancelled) setUser(currentUser)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  // Sync context when the API client clears tokens after a failed refresh.
  useEffect(() => {
    return registerUnauthorizedHandler(() => {
      setUser(null)
    })
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, logout, refreshUser],
  )

  return (
    <AuthContext.Provider value={value}>
      <SessionExpiredListener />
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
