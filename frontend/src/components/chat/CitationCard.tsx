import { formatCitationConfidence, type Citation } from '@/features/chat/types'
import { cn } from '@/utils/cn'

export interface CitationCardProps {
  citation: Citation
  onSelect: (citation: Citation) => void
}

export default function CitationCard({ citation, onSelect }: CitationCardProps) {
  const pageLabel =
    typeof citation.page === 'number' ? `Page ${citation.page}` : 'Page unavailable'

  return (
    <button
      type="button"
      className={cn(
        'w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-left text-sm',
        'transition-colors hover:border-primary-300 hover:bg-primary-50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
        'dark:border-neutral-700 dark:bg-neutral-800/60 dark:hover:border-primary-600 dark:hover:bg-primary-900/20',
        'dark:focus-visible:ring-offset-neutral-900',
      )}
      aria-label={`View citation details for ${citation.source}`}
      onClick={() => onSelect(citation)}
    >
      <p className="font-medium text-neutral-900 dark:text-neutral-100">{citation.source}</p>
      <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">{pageLabel}</p>
      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">
        Confidence: {formatCitationConfidence(citation.confidence)}
      </p>
      <p className="mt-2 text-xs font-medium text-primary-600 dark:text-primary-400">
        View source details
      </p>
    </button>
  )
}
