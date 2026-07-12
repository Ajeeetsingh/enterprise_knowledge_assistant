import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { CitationCard } from '@/components/chat'
import { useToast } from '@/contexts/ToastContext'
import {
  buildCitationViewerParams,
  buildDocumentViewerUrl,
  resolveCitationDocumentId,
} from '@/features/document-viewer'
import { getApiErrorMessage } from '@/services/errorHandler'

import type { Citation } from '../types'

export interface CitationListProps {
  citations: Citation[]
}

export default function CitationList({ citations }: CitationListProps) {
  const navigate = useNavigate()
  const { showError } = useToast()
  const [isOpeningSource, setIsOpeningSource] = useState(false)

  if (citations.length === 0) return null

  async function handleOpenSource(citation: Citation) {
    if (isOpeningSource) return
    setIsOpeningSource(true)
    try {
      const documentId = await resolveCitationDocumentId(citation)
      if (!documentId) {
        showError('Could not find the source document.')
        return
      }

      navigate(buildDocumentViewerUrl(documentId, buildCitationViewerParams(citation)))
    } catch (error) {
      showError(getApiErrorMessage(error))
    } finally {
      setIsOpeningSource(false)
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
        Sources
      </p>
      <ul className="space-y-2" aria-label="Answer citations">
        {citations.map((citation, index) => (
          <li key={`${citation.source}-${index}`}>
            <CitationCard
              citation={citation}
              onOpenSource={(selected) => void handleOpenSource(selected)}
              isOpeningSource={isOpeningSource}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
