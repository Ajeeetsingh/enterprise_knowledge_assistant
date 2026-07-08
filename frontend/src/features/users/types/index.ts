/**
 * User administration types — aligned with backend user management API (Phase 9.4A).
 */

export interface User {
  id: string
  email: string
  username: string | null
  full_name: string
  roles: string[]
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface Role {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface UserListResponse {
  users: User[]
}

export interface RoleListResponse {
  roles: Role[]
}

export interface CreateUserRequest {
  email: string
  password: string
  full_name: string
  username?: string | null
}

/** Successful user creation returns the same shape as {@link User}. */
export type CreateUserResponse = User

export interface AssignRolesRequest {
  roles: string[]
}

export interface AssignRolesResponse {
  user_id: string
  roles: string[]
}

export interface UpdateUserRequest {
  full_name: string
  email: string
  is_active: boolean
}

export function formatUserRoles(roles: string[]): string {
  if (roles.length === 0) return '—'
  return roles.join(', ')
}

export function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
