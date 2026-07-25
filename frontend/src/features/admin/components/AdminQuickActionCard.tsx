import { Link } from 'react-router-dom'

import { cn } from '@/utils/cn'

import { AdminNavIcon, type AdminNavIconName } from './AdminNavIcons'

export interface AdminQuickActionCardProps {
  to: string
  title: string
  description: string
  icon: AdminNavIconName
}

export default function AdminQuickActionCard({
  to,
  title,
  description,
  icon,
}: AdminQuickActionCardProps) {
  return (
    <Link
      to={to}
      className={cn(
        'group flex gap-3 rounded-[var(--radius-lg)] border border-border-subtle',
        'bg-surface-raised p-4 shadow-elevation-sm transition-all duration-150',
        'hover:border-accent/40 hover:shadow-elevation-md hover:bg-accent-muted/30',
        'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
      )}
    >
      <span
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-md',
          'border border-border-subtle bg-overlay text-muted',
          'transition-colors group-hover:border-accent/30 group-hover:text-accent',
        )}
      >
        <AdminNavIcon name={icon} className="size-[18px]" />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-foreground transition-colors group-hover:text-accent">
          {title}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-muted">{description}</span>
      </span>
    </Link>
  )
}
