import { useId, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { InfoIcon } from '@/components/layout/NavIcons'
import { useToast } from '@/contexts/ToastContext'
import {
  buildCitationViewerParams,
  buildDocumentViewerUrl,
  resolveCitationDocumentId,
} from '@/features/document-viewer'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { Citation } from '../types'
import { cn } from '@/utils/cn'

import AnswerDetailsPanel from './AnswerDetailsPanel'
import { type AnswerMetadata } from './AnswerDetailsContent'

export interface AssistantMessagePresentationProps {
  content: ReactNode
  timestamp?: string | null
  metadata: AnswerMetadata
  showMeta?: boolean
  className?: string
}

function formatMessageTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function AssistantMessagePresentation({
  content,
  timestamp,
  metadata,
  showMeta = true,
  className,
}: AssistantMessagePresentationProps) {
  const panelId = useId()
  const navigate = useNavigate()
  const { showError } = useToast()
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [isOpeningSource, setIsOpeningSource] = useState(false)

  const formattedTimestamp = timestamp ? formatMessageTimestamp(timestamp) : null

  async function handleOpenSource(citation: Citation) {
    if (isOpeningSource) return
    setIsOpeningSource(true)
    try {
      const documentId = await resolveCitationDocumentId(citation)
      if (!documentId) {
        showError('Could not find the source document.')
        return
      }

      setDetailsOpen(false)
      navigate(buildDocumentViewerUrl(documentId, buildCitationViewerParams(citation)))
    } catch (error) {
      showError(getApiErrorMessage(error))
    } finally {
      setIsOpeningSource(false)
    }
  }

  function toggleDetails() {
    setDetailsOpen((prev) => !prev)
  }

  return (
    <div className={cn('relative min-w-0', className)}>
      <div className="text-foreground">{content}</div>

      {showMeta && (
        <div
          className={cn(
            'message-meta mt-3 flex items-center justify-between gap-3',
            detailsOpen
              ? 'opacity-100'
              : 'opacity-0 group-hover/message:opacity-100 group-focus-within/message:opacity-100',
          )}
        >
          {formattedTimestamp ? (
            <time dateTime={timestamp ?? undefined}>{formattedTimestamp}</time>
          ) : (
            <span />
          )}

          <button
            type="button"
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-medium',
              'text-subtle transition-colors duration-150',
              'hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              detailsOpen && 'text-accent',
            )}
            aria-expanded={detailsOpen}
            aria-controls={panelId}
            onClick={toggleDetails}
          >
            <InfoIcon />
            Details
          </button>
        </div>
      )}

      {showMeta && (
        <AnswerDetailsPanel
          panelId={panelId}
          isOpen={detailsOpen}
          onClose={() => setDetailsOpen(false)}
          metadata={metadata}
          onOpenSource={(citation) => void handleOpenSource(citation)}
          isOpeningSource={isOpeningSource}
        />
      )}
    </div>
  )
}
