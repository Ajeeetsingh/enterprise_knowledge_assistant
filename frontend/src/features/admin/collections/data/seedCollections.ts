import type { AdminCollection } from '../types'

export const SEED_COLLECTIONS: AdminCollection[] = [
  {
    id: 'col-hr-policies',
    name: 'HR Policies',
    description: 'Human resources policies and employee handbook materials.',
    document_count: 42,
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-03-01T12:00:00Z',
    is_archived: false,
  },
  {
    id: 'col-finance',
    name: 'Finance',
    description: 'Financial policies, budgets, and compliance documents.',
    document_count: 18,
    created_at: '2026-01-12T14:30:00Z',
    updated_at: '2026-02-20T08:15:00Z',
    is_archived: false,
  },
  {
    id: 'col-engineering',
    name: 'Engineering',
    description: 'Engineering standards, runbooks, and technical references.',
    document_count: 27,
    created_at: '2026-01-15T11:00:00Z',
    updated_at: '2026-03-10T16:45:00Z',
    is_archived: false,
  },
  {
    id: 'col-operations',
    name: 'Operations',
    description: 'Operational procedures and service management guides.',
    document_count: 11,
    created_at: '2026-01-18T10:00:00Z',
    updated_at: '2026-02-05T09:30:00Z',
    is_archived: false,
  },
  {
    id: 'col-compliance',
    name: 'Compliance',
    description: 'Regulatory and audit documentation.',
    document_count: 9,
    created_at: '2026-01-20T13:00:00Z',
    updated_at: '2026-01-28T17:00:00Z',
    is_archived: false,
  },
]
