import type { User } from '@/features/users/types'
import { Role, isAdminUser } from '@/types/permissions'
import type { User as AuthUser } from '@/types/auth'

export type AdminRoleFilter = 'ALL' | Role
export type AdminStatusFilter = 'ALL' | 'ACTIVE' | 'DISABLED'

export interface UserFilterState {
  role: AdminRoleFilter
  status: AdminStatusFilter
}

export function getPrimaryRole(roles: string[]): string {
  if (roles.length === 0) return '—'
  return roles[0] ?? '—'
}

export function filterUsersBySearch(users: User[], search: string): User[] {
  const query = search.trim().toLowerCase()
  if (!query) return users

  return users.filter(
    (user) =>
      user.full_name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query),
  )
}

export function filterUsersByRole(users: User[], role: AdminRoleFilter): User[] {
  if (role === 'ALL') return users
  return users.filter((user) => user.roles.includes(role))
}

export function filterUsersByStatus(users: User[], status: AdminStatusFilter): User[] {
  if (status === 'ALL') return users
  if (status === 'ACTIVE') return users.filter((user) => user.is_active)
  return users.filter((user) => !user.is_active)
}

export function applyUserFilters(
  users: User[],
  filters: UserFilterState,
  search = '',
): User[] {
  let result = filterUsersBySearch(users, search)
  result = filterUsersByRole(result, filters.role)
  result = filterUsersByStatus(result, filters.status)
  return result
}

export interface PaginatedSlice<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export function paginateUsers<T>(users: T[], page: number, pageSize: number): PaginatedSlice<T> {
  const total = users.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(page, 1), totalPages)
  const start = (safePage - 1) * pageSize

  return {
    items: users.slice(start, start + pageSize),
    total,
    page: safePage,
    pageSize,
    totalPages,
  }
}

export function canDisableUser(
  targetUserId: string,
  currentUserId: string | undefined,
): boolean {
  return currentUserId !== targetUserId
}

export function canChangeUserRole(
  targetUser: User,
  currentUser: AuthUser | null,
  newRole: string,
): { allowed: boolean; reason?: string } {
  if (!currentUser || currentUser.id !== targetUser.id) {
    return { allowed: true }
  }

  const currentAuthUser: AuthUser = {
    id: currentUser.id,
    email: currentUser.email,
    full_name: currentUser.full_name,
    roles: currentUser.roles,
    is_active: currentUser.is_active,
    is_superuser: currentUser.is_superuser,
  }

  if (isAdminUser(currentAuthUser) && newRole !== Role.Admin) {
    return {
      allowed: false,
      reason: 'You cannot remove your own administrator role.',
    }
  }

  return { allowed: true }
}

export function getDisableBlockReason(
  targetUser: User,
  currentUserId: string | undefined,
): string | undefined {
  if (currentUserId === targetUser.id) {
    return 'You cannot disable your own account.'
  }

  if (!targetUser.is_active) {
    return 'User is already disabled.'
  }

  return undefined
}
