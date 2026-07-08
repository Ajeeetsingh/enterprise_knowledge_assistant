import type { User } from '@/features/users/types'
import { Role } from '@/types/permissions'

export const mockAdminUsers: User[] = [
  {
    id: 'user-1',
    email: 'john@company.com',
    username: null,
    full_name: 'John Doe',
    roles: [Role.Admin],
    is_active: true,
    is_superuser: false,
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-10T10:00:00Z',
  },
  {
    id: 'user-2',
    email: 'jane@company.com',
    username: null,
    full_name: 'Jane Doe',
    roles: [Role.Employee],
    is_active: false,
    is_superuser: false,
    created_at: '2026-02-15T10:00:00Z',
    updated_at: '2026-02-15T10:00:00Z',
  },
  {
    id: 'user-3',
    email: 'hr@company.com',
    username: null,
    full_name: 'HR Manager',
    roles: [Role.HR],
    is_active: true,
    is_superuser: false,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
]
