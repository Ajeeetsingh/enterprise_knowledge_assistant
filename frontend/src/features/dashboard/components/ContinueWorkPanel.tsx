import { Link } from 'react-router-dom'

import Skeleton from '@/components/ui/Skeleton'
import {
  conversationDisplayTitle,
  type Conversation,
} from '@/features/chat/types'
import { cn } from '@/utils/cn'

import { formatRelativeTime } from '../utils/greeting'

export interface ContinueWorkPanelProps {
  conversations: Conversation[]
  isLoading: boolean
}

export default function ContinueWorkPanel({
  conversations,
  isLoading,
}: ContinueWorkPanelProps) {
  const recent = [...conversations]
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    )
    .slice(0, 5)

  return (
    <section
      className={cn(
        'dashboard-panel',
        'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
        'p-5 shadow-elevation-sm',
      )}
      aria-labelledby="dashboard-continue-heading"
    >
      <div className="dashboard-panel__header">
        <h2 id="dashboard-continue-heading" className="dashboard-panel__title">
          Continue your work
        </h2>
        <Link to="/chat" className="dashboard-panel__view-all">
          View all →
        </Link>
      </div>

      {isLoading ? (
        <ul className="mt-4 space-y-3" aria-busy="true" aria-label="Loading conversations">
          {Array.from({ length: 3 }, (_, index) => (
            <li key={index} className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-40" variant="text" />
              <Skeleton className="h-3 w-16" variant="text" />
            </li>
          ))}
        </ul>
      ) : recent.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          You haven&apos;t asked anything yet — try the box above.
        </p>
      ) : (
        <ul className="mt-3 space-y-0.5">
          {recent.map((conversation) => (
            <li key={conversation.id}>
              <Link
                to={`/chat?conversation=${conversation.id}`}
                className={cn(
                  'dashboard-panel__row',
                  'flex items-center justify-between gap-3 py-3 text-sm',
                  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                )}
              >
                <span className="min-w-0 truncate font-medium text-foreground">
                  {conversationDisplayTitle(conversation)}
                </span>
                <time
                  dateTime={conversation.updated_at}
                  className="shrink-0 text-xs text-subtle"
                >
                  {formatRelativeTime(conversation.updated_at)}
                </time>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
