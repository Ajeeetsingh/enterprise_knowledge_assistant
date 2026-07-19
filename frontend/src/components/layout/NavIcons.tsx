import type { ReactNode } from 'react'

import { cn } from '@/utils/cn'

export type NavIconName =
  | 'dashboard'
  | 'chat'
  | 'documents'
  | 'admin'
  | 'users'
  | 'monitoring'
  | 'profile'

const ICON_PATHS: Record<NavIconName, ReactNode> = {
  dashboard: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5Z"
    />
  ),
  chat: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8 10h8M8 14h5M6 4h12a2 2 0 0 1 2 2v12l-3-2-3 2-3-2-3 2V6a2 2 0 0 1 2-2Z"
    />
  ),
  documents: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8 4h8l4 4v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm8 0v4h4"
    />
  ),
  admin: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 3 4 7v6c0 4.4 3.6 7.5 8 9 4.4-1.5 8-4.6 8-9V7l-8-4Zm0 6.5a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z"
    />
  ),
  users: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M16 19v-1a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v1M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8 8v-1a3 3 0 0 0-2-2.83M16 4.17a3 3 0 0 1 0 5.66"
    />
  ),
  monitoring: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4 19h16M6 16l3-5 3 3 4-7 3 4"
    />
  ),
  profile: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4 0-7 2-7 4v1h14v-1c0-2-3-4-7-4Z"
    />
  ),
}

export const NAV_ICON_BY_PATH: Record<string, NavIconName> = {
  '/dashboard': 'dashboard',
  '/chat': 'chat',
  '/documents': 'documents',
  '/admin': 'admin',
  '/admin/users': 'users',
  '/users': 'users',
  '/monitoring': 'monitoring',
  '/profile': 'profile',
}

export function NavIcon({
  name,
  className,
}: {
  name: NavIconName
  className?: string
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-[18px] shrink-0', className)}
      aria-hidden
    >
      {ICON_PATHS[name]}
    </svg>
  )
}

export function HamburgerIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5', className)}
      aria-hidden
    >
      <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

export function ConversationsIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5', className)}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7 8h10M7 12h7M5 5h14a2 2 0 0 1 2 2v10l-3-2-3 2-3-2-3 2V7a2 2 0 0 1 2-2Z"
      />
    </svg>
  )
}

export function InfoIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-4', className)}
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" />
      <path strokeLinecap="round" d="M12 10v6M12 7h.01" />
    </svg>
  )
}

export function ExternalLinkIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-4', className)}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M14 4h6v6M10 14 20 4M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"
      />
    </svg>
  )
}

export function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5', className)}
      aria-hidden
    >
      <circle cx="12" cy="12" r="4" />
      <path
        strokeLinecap="round"
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
      />
    </svg>
  )
}

export function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5', className)}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20 14.5A8.5 8.5 0 0 1 9.5 4 7 7 0 1 0 20 14.5Z"
      />
    </svg>
  )
}

export function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-4', className)}
      aria-hidden
    >
      <path strokeLinecap="round" d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function ArrowUpIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5', className)}
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  )
}
