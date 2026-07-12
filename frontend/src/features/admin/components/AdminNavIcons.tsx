import type { ReactNode } from 'react'

import { cn } from '@/utils/cn'

export type AdminNavIconName =
  | 'dashboard'
  | 'documents'
  | 'uploads'
  | 'users'
  | 'collections'
  | 'user-analytics'
  | 'ai-analytics'
  | 'knowledge-analytics'
  | 'system-monitoring'
  | 'error-analytics'
  | 'reports'

/** One-to-one icon mapping per admin nav path — never derived from label text. */
export const ADMIN_NAV_ICON_BY_PATH: Record<string, AdminNavIconName> = {
  '/admin': 'dashboard',
  '/admin/documents': 'documents',
  '/admin/uploads': 'uploads',
  '/admin/users': 'users',
  '/admin/collections': 'collections',
  '/admin/analytics': 'user-analytics',
  '/admin/analytics/ai': 'ai-analytics',
  '/admin/analytics/knowledge': 'knowledge-analytics',
  '/admin/analytics/monitoring': 'system-monitoring',
  '/admin/analytics/errors': 'error-analytics',
  '/admin/reports': 'reports',
}

const ICON_PATHS: Record<AdminNavIconName, ReactNode> = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </>
  ),
  documents: (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 2v6h6M10 13H8M16 13h-2M10 17H8M16 17h-2" />
    </>
  ),
  uploads: (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 13v8M8 17l4-4 4 4" />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"
      />
    </>
  ),
  users: (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  collections: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"
    />
  ),
  'user-analytics': (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 20V10M12 20V4M6 20v-6" />
    </>
  ),
  'ai-analytics': (
    <>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0Z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 3v4M22 5h-4" />
    </>
  ),
  'knowledge-analytics': (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 7v14" />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3Z"
      />
    </>
  ),
  'system-monitoring': (
    <path strokeLinecap="round" strokeLinejoin="round" d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" />
  ),
  'error-analytics': (
    <>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4M12 17h.01" />
    </>
  ),
  reports: (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 2v6h6M12 18v-6M9 15l3 3 3-3" />
    </>
  ),
}

export function AdminNavIcon({
  name,
  className,
}: {
  name: AdminNavIconName
  className?: string
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('nav-icon', className)}
      aria-hidden
    >
      {ICON_PATHS[name]}
    </svg>
  )
}
