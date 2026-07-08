import { describe, expect, it } from 'vitest'

import { Role } from '@/types/permissions'

import { mockAdminUsers } from '../test/userFixtures'
import {
  applyUserFilters,
  canChangeUserRole,
  canDisableUser,
  filterUsersByRole,
  filterUsersBySearch,
  filterUsersByStatus,
} from './userFilters'

describe('userFilters', () => {
  it('filters users by search term', () => {
    expect(filterUsersBySearch(mockAdminUsers, 'john')).toHaveLength(1)
    expect(filterUsersBySearch(mockAdminUsers, 'company.com')).toHaveLength(3)
  })

  it('filters users by role', () => {
    expect(filterUsersByRole(mockAdminUsers, Role.Admin)).toHaveLength(1)
    expect(filterUsersByRole(mockAdminUsers, Role.Employee)).toHaveLength(1)
  })

  it('filters users by status', () => {
    expect(filterUsersByStatus(mockAdminUsers, 'ACTIVE')).toHaveLength(2)
    expect(filterUsersByStatus(mockAdminUsers, 'DISABLED')).toHaveLength(1)
  })

  it('applies combined filters', () => {
    const result = applyUserFilters(
      mockAdminUsers,
      { role: Role.Employee, status: 'DISABLED' },
      'jane',
    )

    expect(result).toHaveLength(1)
    expect(result[0]?.full_name).toBe('Jane Doe')
  })
})

describe('userProtection', () => {
  it('prevents self-disable', () => {
    expect(canDisableUser('user-1', 'user-1')).toBe(false)
    expect(canDisableUser('user-2', 'user-1')).toBe(true)
  })

  it('prevents removing own admin role', () => {
    const adminUser = mockAdminUsers[0]!
    const result = canChangeUserRole(adminUser, {
      id: adminUser.id,
      email: adminUser.email,
      full_name: adminUser.full_name,
      roles: adminUser.roles,
      is_active: true,
      is_superuser: false,
    }, Role.Employee)

    expect(result.allowed).toBe(false)
    expect(result.reason).toMatch(/administrator role/i)
  })
})
