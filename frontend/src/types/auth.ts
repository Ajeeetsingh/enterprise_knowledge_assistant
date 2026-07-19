/**
 * Authentication types — aligned with backend schemas (Phase 8.4).
 */

export interface User {
  id: string
  email: string
  full_name: string
  roles: string[]
  is_active: boolean
  is_superuser: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  username?: string | null
}

export interface RegisterResponse {
  id: string
  email: string
  full_name: string
  message: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface RefreshResponse {
  access_token: string
  token_type: string
}

export interface LogoutResponse {
  message: string
}
