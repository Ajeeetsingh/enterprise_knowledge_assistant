import { Link } from 'react-router-dom'

import { NavIcon } from '@/components/layout/NavIcons'
import MetricIcon from '@/components/ui/MetricIcon'
import { Permission, hasPermission, isAdminUser } from '@/types/permissions'
import type { User } from '@/types/auth'
import { cn } from '@/utils/cn'

export interface QuickActionsGridProps {
  user: User | null
}

const focusRing =
  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]'

export default function QuickActionsGrid({ user }: QuickActionsGridProps) {
  const canUpload = hasPermission(user, Permission.DocumentCreate)
  const canViewAnalytics = isAdminUser(user)

  const actions = [
    {
      to: '/chat',
      label: 'Ask a question',
      description: 'Open Knowra',
      icon: <NavIcon name="chat" className="size-5 text-accent" />,
      show: true,
    },
    {
      to: isAdminUser(user) ? '/admin/uploads' : '/documents',
      label: 'Upload documents',
      description: 'Add files to the knowledge base',
      icon: <MetricIcon name="storage" className="size-5 text-accent" />,
      show: canUpload,
    },
    {
      to: '/documents',
      label: 'Browse knowledge',
      description: 'View documents you can access',
      icon: <NavIcon name="documents" className="size-5 text-accent" />,
      show: true,
    },
    {
      to: '/admin/analytics',
      label: 'View analytics',
      description: 'Organisation-wide insights',
      icon: <MetricIcon name="monitoring" className="size-5 text-accent" />,
      show: canViewAnalytics,
    },
  ].filter((action) => action.show)

  return (
    <section aria-labelledby="dashboard-actions-heading">
      <h2
        id="dashboard-actions-heading"
        className="text-sm font-semibold tracking-tight text-foreground"
      >
        Quick actions
      </h2>
      <ul className="mt-3 grid grid-cols-2 gap-3">
        {actions.map((action) => (
          <li key={`${action.to}-${action.label}`}>
            <Link
              to={action.to}
              className={cn(
                'flex h-full flex-col gap-2 rounded-[var(--radius-lg)] border border-border-subtle',
                'bg-surface-raised p-4 shadow-elevation-sm transition-[border-color,transform]',
                'hover:-translate-y-0.5 hover:border-border-default',
                focusRing,
              )}
            >
              {action.icon}
              <span className="text-sm font-semibold text-foreground">{action.label}</span>
              <span className="text-xs text-muted">{action.description}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
