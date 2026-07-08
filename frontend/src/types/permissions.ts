/**
 * Role and permission types — aligned with backend RBAC (Phase 8.5).
 *
 * Utility functions operate on the authenticated user's role list from /auth/me.
 * No backend calls are made here.
 */

import type { User } from '@/types/auth'

/** System roles seeded in the backend identity layer. */
export enum Role {
  Admin = 'Admin',
  HR = 'HR',
  Finance = 'Finance',
  Employee = 'Employee',
}

/** Canonical permission identifiers (resource:action). */
export enum Permission {
  DocumentCreate = 'document:create',
  DocumentRead = 'document:read',
  DocumentUpdate = 'document:update',
  DocumentDelete = 'document:delete',
  KnowledgeQuery = 'knowledge:query',
  KnowledgeManage = 'knowledge:manage',
  UserView = 'user:view',
  UserCreate = 'user:create',
  UserUpdate = 'user:update',
  UserDelete = 'user:delete',
  AuditView = 'audit:view',
}

/** Static role-to-permission map mirroring backend ROLE_PERMISSIONS. */
export const ROLE_PERMISSIONS: Readonly<Record<Role, readonly Permission[]>> = {
  [Role.Admin]: Object.values(Permission),
  [Role.HR]: [
    Permission.DocumentCreate,
    Permission.DocumentRead,
    Permission.DocumentUpdate,
    Permission.KnowledgeQuery,
  ],
  [Role.Finance]: [Permission.DocumentRead, Permission.KnowledgeQuery],
  [Role.Employee]: [Permission.DocumentRead, Permission.KnowledgeQuery],
}

const ROLE_ALIASES: Readonly<Record<string, Role>> = {
  admin: Role.Admin,
  administrator: Role.Admin,
  hr: Role.HR,
  finance: Role.Finance,
  employee: Role.Employee,
}

function resolveRole(role: Role | string): Role | null {
  if (Object.values(Role).includes(role as Role)) {
    return role as Role
  }
  const normalised = role.trim().toLowerCase()
  return ROLE_ALIASES[normalised] ?? null
}

function resolvePermission(permission: Permission | string): Permission | null {
  const values = Object.values(Permission) as string[]
  if (values.includes(permission)) {
    return permission as Permission
  }
  return null
}

function normaliseUserRoles(user: User): Role[] {
  const resolved: Role[] = []
  for (const name of user.roles) {
    const role = resolveRole(name)
    if (role && !resolved.includes(role)) {
      resolved.push(role)
    }
  }
  return resolved
}

function permissionsForRoles(roles: Role[]): Set<Permission> {
  const granted = new Set<Permission>()
  for (const role of roles) {
    for (const permission of ROLE_PERMISSIONS[role]) {
      granted.add(permission)
    }
  }
  return granted
}

/** Return true when *user* holds *role* (case-insensitive, alias-aware). */
export function hasRole(user: User | null, role: Role | string): boolean {
  if (!user) return false
  const target = resolveRole(role)
  if (!target) return false
  return normaliseUserRoles(user).includes(target)
}

/** Return true when *user* holds *permission* via any assigned role. Superusers pass all checks. */
export function hasPermission(user: User | null, permission: Permission | string): boolean {
  if (!user) return false
  if (user.is_superuser) return true

  const target = resolvePermission(permission)
  if (!target) return false

  const roles = normaliseUserRoles(user)
  return permissionsForRoles(roles).has(target)
}

/** Return true when *user* is an administrator (Admin role or superuser). */
export function isAdminUser(user: User | null): boolean {
  if (!user) return false
  if (user.is_superuser) return true
  return hasRole(user, Role.Admin)
}

/** Return true when *user* may see a sidebar item restricted by {@link Role}. */
export function canAccessNavItem(
  user: User | null,
  allowedRoles: readonly Role[] | undefined,
): boolean {
  if (!allowedRoles?.length) return true
  if (!user) return false
  if (user.is_superuser) return true
  return allowedRoles.some((role) => hasRole(user, role))
}

/** Return all permissions granted to *user* through their roles. */
export function getUserPermissions(user: User | null): Permission[] {
  if (!user) return []
  if (user.is_superuser) return Object.values(Permission)
  return [...permissionsForRoles(normaliseUserRoles(user))]
}
