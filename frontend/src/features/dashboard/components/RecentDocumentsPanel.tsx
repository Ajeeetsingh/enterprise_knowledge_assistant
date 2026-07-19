import { Link } from 'react-router-dom'

import Skeleton from '@/components/ui/Skeleton'
import DocumentStatusBadge from '@/features/documents/components/DocumentStatusBadge'
import type { Document } from '@/features/documents/types'
import { cn } from '@/utils/cn'

import { formatRelativeTime } from '../utils/greeting'

export interface RecentDocumentsPanelProps {
  documents: Document[]
  isLoading: boolean
}

export default function RecentDocumentsPanel({
  documents,
  isLoading,
}: RecentDocumentsPanelProps) {
  const recent = [...documents]
    .sort(
      (a, b) =>
        new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime(),
    )
    .slice(0, 5)

  return (
    <section
      className={cn(
        'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
        'p-5 shadow-elevation-sm',
      )}
      aria-labelledby="dashboard-documents-heading"
    >
      <h2
        id="dashboard-documents-heading"
        className="text-sm font-semibold tracking-tight text-foreground"
      >
        Recent documents
      </h2>

      {isLoading ? (
        <ul className="mt-4 space-y-3" aria-busy="true" aria-label="Loading documents">
          {Array.from({ length: 3 }, (_, index) => (
            <li key={index} className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-40" variant="text" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </li>
          ))}
        </ul>
      ) : recent.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No documents available yet. Ask an admin to upload some, or check back soon.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-border-subtle">
          {recent.map((document) => (
            <li key={document.document_id}>
              <Link
                to={`/documents/${document.document_id}`}
                className={cn(
                  'flex items-center justify-between gap-3 py-3',
                  'rounded-md transition-colors hover:opacity-90',
                  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                )}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">
                    {document.filename}
                  </p>
                  <p className="mt-0.5 text-xs text-subtle">
                    {formatRelativeTime(document.uploaded_at)}
                  </p>
                </div>
                <DocumentStatusBadge status={document.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
