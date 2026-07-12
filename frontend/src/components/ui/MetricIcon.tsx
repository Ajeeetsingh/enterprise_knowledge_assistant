import { type ReactNode } from 'react'

import { cn } from '@/utils/cn'

export type MetricIconName =
  | 'users'
  | 'documents'
  | 'storage'
  | 'errors'
  | 'success'
  | 'ai'
  | 'time'
  | 'search'
  | 'collections'
  | 'monitoring'
  | 'reports'

const ICON_PATHS: Record<MetricIconName, ReactNode> = {
  users: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M16 19v-1a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v1M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8 8v-1a3 3 0 0 0-2-2.83M16 4.17a3 3 0 0 1 0 5.66"
    />
  ),
  documents: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8 4h8l4 4v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm8 0v4h4"
    />
  ),
  storage: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4 7v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7M4 7l2-3h12l2 3M12 11v4"
    />
  ),
  errors: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 9v4m0 4h.01M10.29 3.86 2.82 17a2 2 0 0 0 1.71 3h14.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
    />
  ),
  success: (
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  ),
  ai: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"
    />
  ),
  time: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 8v4l3 2m9-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
    />
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path strokeLinecap="round" d="M20 20l-3-3" />
    </>
  ),
  collections: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4 7h16M4 12h10M4 17h16"
    />
  ),
  monitoring: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M4 19h16M6 16l3-5 3 3 4-7 3 4"
    />
  ),
  reports: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 17v-6m3 6V7m3 10v-4M5 4h14v16H5z"
    />
  ),
}

export interface MetricIconProps {
  name: MetricIconName
  className?: string
  tone?: 'default' | 'good' | 'warn' | 'bad'
}

const toneClass: Record<NonNullable<MetricIconProps['tone']>, string> = {
  default: 'text-muted',
  good: 'text-status-good',
  warn: 'text-status-warn',
  bad: 'text-status-bad',
}

export default function MetricIcon({ name, className, tone = 'default' }: MetricIconProps) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-[18px] shrink-0', toneClass[tone], className)}
    >
      {ICON_PATHS[name]}
    </svg>
  )
}
