import type { User } from '@/types/auth'
import { Role } from '@/types/permissions'

export const adminUser: User = {
  id: 'admin-1',
  email: 'admin@example.com',
  full_name: 'Admin User',
  roles: [Role.Admin],
  is_active: true,
  is_superuser: false,
}

export const employeeUser: User = {
  id: 'emp-1',
  email: 'employee@example.com',
  full_name: 'Employee User',
  roles: [Role.Employee],
  is_active: true,
  is_superuser: false,
}
