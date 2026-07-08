import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import {
  formatCitationConfidence,
  type CitationDetails,
} from '@/features/chat/types'
import { cn } from '@/utils/cn'

export interface CitationModalProps {
  isOpen: boolean
  details: CitationDetails | null
  isLoading: boolean
  error: string | null
  onClose: () => void
  onRetry: () => void
}

function MetadataSection({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata).filter(
    ([, value]) => value !== null && value !== undefined && value !== '',
  )

  if (entries.length === 0) return null

  return (
    <div>
      <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Metadata</dt>
      <dd className="mt-1 space-y-1 text-sm text-neutral-700 dark:text-neutral-200">
        {entries.map(([key, value]) => (
          <p key={key}>
            <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
            {typeof value === 'string' || typeof value === 'number'
              ? String(value)
              : JSON.stringify(value)}
          </p>
        ))}
      </dd>
    </div>
  )
}

export default function CitationModal({
  isOpen,
  details,
  isLoading,
  error,
  onClose,
  onRetry,
}: CitationModalProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return

    closeButtonRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isLoading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isLoading, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isLoading) onClose()
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className={cn(
          'w-full max-w-lg rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
            Citation Details
          </h2>
          <Button
            ref={closeButtonRef}
            type="button"
            variant="secondary"
            size="sm"
            disabled={isLoading}
            aria-label="Close citation details"
            onClick={onClose}
          >
            Close
          </Button>
        </div>

        <div id={descriptionId} className="mt-4">
          {isLoading && (
            <div className="flex items-center gap-2 py-6" role="status">
              <Spinner size="sm" label="Loading citation details" />
              <span className="text-sm text-neutral-600 dark:text-neutral-300">
                Loading citation details…
              </span>
            </div>
          )}

          {!isLoading && error && (
            <div
              role="alert"
              className="flex flex-col gap-3 rounded-md border border-error-500/30 bg-error-50 px-4 py-3 dark:bg-error-700/10"
            >
              <p className="text-sm text-error-700 dark:text-error-400">{error}</p>
              <Button variant="secondary" size="sm" className="self-start" onClick={onRetry}>
                Retry
              </Button>
            </div>
          )}

          {!isLoading && !error && details && (
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
                  Document
                </dt>
                <dd className="mt-1 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {details.source}
                </dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
                  Page
                </dt>
                <dd className="mt-1 text-sm text-neutral-700 dark:text-neutral-200">
                  {details.page != null
                    ? details.page
                    : 'Page information unavailable.'}
                </dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
                  Confidence
                </dt>
                <dd className="mt-1 text-sm text-neutral-700 dark:text-neutral-200">
                  {formatCitationConfidence(details.confidence)}
                </dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
                  Excerpt
                </dt>
                <dd className="mt-1 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-200">
                  {details.excerpt ?? 'No excerpt available.'}
                </dd>
              </div>

              {details.metadata && <MetadataSection metadata={details.metadata} />}
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}
