/**
 * Authentication API — wraps backend /auth/* endpoints (Phase 8.4).
 */

import type {
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RefreshRequest,
  RefreshResponse,
  User,
} from '@/types/auth'
import { toApiError } from '@/utils/apiError'

import apiClient from './api'

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  try {
    const { data } = await apiClient.post<LoginResponse>('/auth/login', credentials)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function refresh(refreshToken: string): Promise<RefreshResponse> {
  try {
    const body: RefreshRequest = { refresh_token: refreshToken }
    const { data } = await apiClient.post<RefreshResponse>('/auth/refresh', body)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function logout(): Promise<LogoutResponse> {
  try {
    const { data } = await apiClient.post<LogoutResponse>('/auth/logout')
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getCurrentUser(): Promise<User> {
  try {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  } catch (error) {
    throw toApiError(error)
  }
}
