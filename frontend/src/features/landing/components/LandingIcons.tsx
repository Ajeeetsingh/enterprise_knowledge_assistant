import type { ReactNode } from 'react'

import { cn } from '@/utils/cn'

function IconShell({
  className,
  children,
}: {
  className?: string | undefined
  children: ReactNode
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={cn('size-5 shrink-0', className)}
      aria-hidden
    >
      {children}
    </svg>
  )
}

export function MessageSquareIcon({ className }: { className?: string }) {
  return (
    <IconShell className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8 10h8M8 14h5M6 4h12a2 2 0 0 1 2 2v12l-3-2-3 2-3-2-3 2V6a2 2 0 0 1 2-2Z"
      />
    </IconShell>
  )
}

export function FileTextIcon({ className }: { className?: string }) {
  return (
    <IconShell className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8 4h8l4 4v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm8 0v4h4M9 13h6M9 17h4"
      />
    </IconShell>
  )
}

export function UploadCloudIcon({ className }: { className?: string }) {
  return (
    <IconShell className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 16V8m0 0 3 3M12 8 9 11M7 19h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.2 8.7 4.5 4.5 0 0 0 7 19Z"
      />
    </IconShell>
  )
}

export function ShieldCheckIcon({ className }: { className?: string }) {
  return (
    <IconShell className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3 4 7v6c0 4.4 3.6 7.5 8 9 4.4-1.5 8-4.6 8-9V7l-8-4Z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 12 2 2 4-4" />
    </IconShell>
  )
}
