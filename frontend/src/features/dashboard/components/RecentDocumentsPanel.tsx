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

function FileTypeIcon({ filename }: { filename: string }) {
  const ext = filename.includes('.')
    ? filename.split('.').pop()?.toLowerCase() ?? ''
    : ''
  const isPdf = ext === 'pdf'
  const label = isPdf ? 'PDF' : ext === 'doc' || ext === 'docx' ? 'DOC' : 'FILE'

  return (
    <span
      className={cn(
        'dashboard-file-icon',
        isPdf && 'dashboard-file-icon--pdf',
        (ext === 'doc' || ext === 'docx') && 'dashboard-file-icon--doc',
      )}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="size-3.5">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8 4h8l4 4v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm8 0v4h4"
        />
      </svg>
      <span className="dashboard-file-icon__ext">{label}</span>
    </span>
  )
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
        'dashboard-panel dashboard-recent-docs',
        'rounded-[var(--radius-lg)] border border-border-subtle bg-surface-raised',
        'p-5 shadow-elevation-sm',
      )}
      aria-labelledby="dashboard-documents-heading"
    >
      <div className="dashboard-panel__header">
        <h2 id="dashboard-documents-heading" className="dashboard-panel__title">
          Recent documents
        </h2>
        <Link to="/documents" className="dashboard-panel__view-all">
          View all →
        </Link>
      </div>

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
        <ul className="mt-3 space-y-0.5">
          {recent.map((document) => (
            <li key={document.document_id}>
              <Link
                to={`/documents/${document.document_id}`}
                className={cn(
                  'dashboard-panel__row',
                  'flex items-center justify-between gap-3 py-3',
                  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                )}
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <FileTypeIcon filename={document.filename} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {document.filename}
                    </p>
                    <p className="mt-0.5 text-xs text-subtle">
                      {formatRelativeTime(document.uploaded_at)}
                    </p>
                  </div>
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
