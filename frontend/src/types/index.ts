/**
 * Shared application-wide TypeScript types.
 *
 * Feature-specific types live alongside their feature modules.
 * Only truly cross-cutting types belong here.
 */

export type { ApiError } from './api'
export type {
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RefreshRequest,
  RefreshResponse,
  User,
} from './auth'

export { Permission, Role, ROLE_PERMISSIONS, canAccessNavItem, getUserPermissions, hasPermission, hasRole, isAdminUser } from './permissions'
