import type { ReactNode } from 'react'

import { ExternalLinkIcon } from '@/components/layout/NavIcons'
import { formatCitationConfidence, type Citation } from '@/features/chat/types'
import { cn } from '@/utils/cn'

export interface AnswerMetadata {
  confidence_score?: number | null
  citations?: Citation[]
  retrieval_score?: number | null
  llm_model?: string | null
  latency_ms?: number | null
  retrieved_chunks?: Array<{ chunk_id: string; score?: number | null }> | null
  reasoning?: Record<string, unknown> | null
}

export interface AnswerDetailsContentProps {
  metadata: AnswerMetadata
  onOpenSource?: (citation: Citation) => void
  isOpeningSource?: boolean
  className?: string
}

function MetadataField({
  label,
  value,
}: {
  label: string
  value: ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <dt className="text-xs text-neutral-500 dark:text-neutral-400">{label}</dt>
      <dd className="text-right text-xs font-medium text-neutral-800 dark:text-neutral-100">
        {value}
      </dd>
    </div>
  )
}

function formatLatency(latencyMs: number): string {
  if (latencyMs >= 1000) {
    return `${(latencyMs / 1000).toFixed(1)}s`
  }
  return `${Math.round(latencyMs)}ms`
}

function excerptHighlights(excerpt: string): string[] {
  return excerpt
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 4)
}

export default function AnswerDetailsContent({
  metadata,
  onOpenSource,
  isOpeningSource = false,
  className,
}: AnswerDetailsContentProps) {
  const citations = metadata.citations ?? []
  const hasConfidence = metadata.confidence_score != null
  const hasRetrievalScore = metadata.retrieval_score != null
  const hasLlmModel = Boolean(metadata.llm_model)
  const hasLatency = metadata.latency_ms != null
  const hasRetrievedChunks = Boolean(metadata.retrieved_chunks?.length)
  const hasReasoning =
    metadata.reasoning != null && Object.keys(metadata.reasoning).length > 0

  const hasTechnicalDetails =
    hasRetrievalScore || hasLlmModel || hasLatency || hasRetrievedChunks || hasReasoning

  return (
    <div className={cn('space-y-5', className)}>
      {hasConfidence && (
        <section aria-label="Answer confidence">
          <h4 className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            Confidence
          </h4>
          <p className="mt-1 text-sm text-neutral-800 dark:text-neutral-100">
            {formatCitationConfidence(metadata.confidence_score!)}
          </p>
        </section>
      )}

      <section aria-label="Answer sources">
        <h4 className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
          Sources
        </h4>
        {citations.length === 0 ? (
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            No sources were attached to this answer.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {citations.map((citation, index) => {
              const pageLabel =
                typeof citation.page === 'number'
                  ? `Page ${citation.page}`
                  : 'Page unavailable'
              const highlights = excerptHighlights(citation.excerpt)

              return (
                <li
                  key={`${citation.source}-${index}`}
                  className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-3 dark:border-neutral-700 dark:bg-neutral-800/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
                        {citation.source}
                      </p>
                      <p className="mt-0.5 text-xs text-neutral-600 dark:text-neutral-400">
                        {pageLabel}
                      </p>
                    </div>
                    {onOpenSource && (
                      <button
                        type="button"
                        className={cn(
                          'inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
                          'text-primary-600 transition-colors duration-200 hover:bg-primary-50',
                          'dark:text-primary-400 dark:hover:bg-primary-900/20',
                          isOpeningSource && 'cursor-wait opacity-70',
                        )}
                        disabled={isOpeningSource}
                        onClick={() => onOpenSource(citation)}
                      >
                        <ExternalLinkIcon />
                        Open Source
                      </button>
                    )}
                  </div>

                  {highlights.length > 0 && (
                    <div className="mt-3 border-t border-neutral-200 pt-3 dark:border-neutral-700">
                      <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                        Highlights from source
                      </p>
                      <ul className="mt-2 space-y-1.5">
                        {highlights.map((highlight) => (
                          <li
                            key={highlight}
                            className="text-xs leading-relaxed text-neutral-700 dark:text-neutral-300"
                          >
                            • {highlight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-500">
                    Confidence: {formatCitationConfidence(citation.confidence)}
                  </p>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {hasTechnicalDetails && (
        <section aria-label="Technical details">
          <h4 className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            Technical details
          </h4>
          <dl className="mt-1 divide-y divide-neutral-200 dark:divide-neutral-700">
            {hasRetrievalScore && (
              <MetadataField
                label="Retrieval score"
                value={formatCitationConfidence(metadata.retrieval_score!)}
              />
            )}
            {hasLlmModel && (
              <MetadataField label="LLM model" value={metadata.llm_model} />
            )}
            {hasLatency && (
              <MetadataField
                label="Latency"
                value={formatLatency(metadata.latency_ms!)}
              />
            )}
            {hasRetrievedChunks && (
              <div className="py-2">
                <dt className="text-xs text-neutral-500 dark:text-neutral-400">
                  Retrieved chunks
                </dt>
                <dd className="mt-1 space-y-1">
                  {metadata.retrieved_chunks!.map((chunk) => (
                    <p
                      key={chunk.chunk_id}
                      className="text-xs text-neutral-700 dark:text-neutral-200"
                    >
                      {chunk.chunk_id}
                      {chunk.score != null
                        ? ` · ${formatCitationConfidence(chunk.score)}`
                        : ''}
                    </p>
                  ))}
                </dd>
              </div>
            )}
            {hasReasoning && (
              <div className="py-2">
                <dt className="text-xs text-neutral-500 dark:text-neutral-400">
                  Reasoning metadata
                </dt>
                <dd className="mt-1 space-y-1 text-xs text-neutral-700 dark:text-neutral-200">
                  {Object.entries(metadata.reasoning!).map(([key, value]) => (
                    <p key={key}>
                      <span className="font-medium capitalize">
                        {key.replace(/_/g, ' ')}:
                      </span>{' '}
                      {typeof value === 'string' || typeof value === 'number'
                        ? String(value)
                        : JSON.stringify(value)}
                    </p>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </section>
      )}
    </div>
  )
}
