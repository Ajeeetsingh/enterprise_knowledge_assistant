/**
 * JWT token persistence via localStorage (Phase 8.4).
 */

const ACCESS_TOKEN_KEY = 'eka_access_token'
const REFRESH_TOKEN_KEY = 'eka_refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function removeAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function removeRefreshToken(): void {
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function clearTokens(): void {
  removeAccessToken()
  removeRefreshToken()
}

export function hasAccessToken(): boolean {
  return getAccessToken() !== null
}

export function hasRefreshToken(): boolean {
  return getRefreshToken() !== null
}
