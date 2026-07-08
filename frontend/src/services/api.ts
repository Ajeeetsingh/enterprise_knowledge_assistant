/**
 * Axios base client with auth interceptors (Phase 8.4).
 *
 * - Request interceptor attaches Bearer access token when available.
 * - Response interceptor attempts a single token refresh on 401, then retries.
 * - Refresh failure clears tokens and notifies the registered auth handler.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import type { RefreshResponse } from '@/types/auth'

import * as authStorage from './authStorage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined

if (!API_BASE_URL) {
  console.warn(
    '[api] VITE_API_BASE_URL is not set. ' +
      'Copy .env.example to .env and set the variable.',
  )
}

const resolvedBaseUrl = API_BASE_URL ?? '/api/v1'

const apiClient = axios.create({
  baseURL: resolvedBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
})

type UnauthorizedHandler = () => void

const unauthorizedHandlers = new Set<UnauthorizedHandler>()

/** Register a callback invoked when refresh fails and the session is cleared. */
export function registerUnauthorizedHandler(handler: UnauthorizedHandler): () => void {
  unauthorizedHandlers.add(handler)
  return () => {
    unauthorizedHandlers.delete(handler)
  }
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

let isRefreshing = false
let refreshQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processRefreshQueue(error: unknown, token: string | null): void {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error || !token) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  refreshQueue = []
}

function clearSession(): void {
  authStorage.clearTokens()
  unauthorizedHandlers.forEach((handler) => handler())
}

async function performTokenRefresh(): Promise<string> {
  const refreshToken = authStorage.getRefreshToken()
  if (!refreshToken) {
    throw new Error('No refresh token available.')
  }

  // Use a plain axios call to avoid interceptor recursion on /auth/refresh.
  const { data } = await axios.post<RefreshResponse>(
    `${resolvedBaseUrl}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' }, timeout: 30_000 },
  )

  authStorage.setAccessToken(data.access_token)
  return data.access_token
}

apiClient.interceptors.request.use((config) => {
  const token = authStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    // Let the runtime set multipart/form-data with the correct boundary.
    delete config.headers['Content-Type']
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined

    if (!originalRequest || error.response?.status !== 401) {
      return Promise.reject(error)
    }

    // Do not retry refresh or login endpoints.
    const url = originalRequest.url ?? ''
    if (url.includes('/auth/refresh') || url.includes('/auth/login')) {
      if (url.includes('/auth/refresh')) {
        clearSession()
      }
      return Promise.reject(error)
    }

    if (originalRequest._retry) {
      clearSession()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return apiClient(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const newToken = await performTokenRefresh()
      processRefreshQueue(null, newToken)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      processRefreshQueue(refreshError, null)
      clearSession()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default apiClient
