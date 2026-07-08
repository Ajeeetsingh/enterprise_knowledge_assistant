import { useState } from 'react'

import { CitationCard, CitationModal } from '@/components/chat'

import { useCitationDetails } from '../hooks/useCitationDetails'
import type { Citation } from '../types'

export interface CitationListProps {
  citations: Citation[]
}

export default function CitationList({ citations }: CitationListProps) {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const isCitationModalOpen = selectedCitation !== null

  const { details, isLoading, error, retry } = useCitationDetails(selectedCitation)

  if (citations.length === 0) return null

  function handleSelect(citation: Citation) {
    setSelectedCitation(citation)
  }

  function handleCloseModal() {
    if (isLoading) return
    setSelectedCitation(null)
  }

  return (
    <>
      <div className="mt-3 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
          Sources
        </p>
        <ul className="space-y-2" aria-label="Answer citations">
          {citations.map((citation, index) => (
            <li key={`${citation.source}-${index}`}>
              <CitationCard citation={citation} onSelect={handleSelect} />
            </li>
          ))}
        </ul>
      </div>

      <CitationModal
        isOpen={isCitationModalOpen}
        details={details}
        isLoading={isLoading}
        error={error}
        onClose={handleCloseModal}
        onRetry={retry}
      />
    </>
  )
}
