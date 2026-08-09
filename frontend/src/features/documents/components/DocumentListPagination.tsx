import Button from '@/components/ui/Button'

export interface DocumentListPaginationProps {
  page: number
  totalPages: number
  totalResults: number
  onPrevious: () => void
  onNext: () => void
}

export default function DocumentListPagination({
  page,
  totalPages,
  totalResults,
  onPrevious,
  onNext,
}: DocumentListPaginationProps) {
  if (totalPages <= 1) return null

  return (
    <nav
      aria-label="Document pagination"
      className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-neutral-600 dark:text-neutral-300">
        Page <span className="font-medium text-neutral-900 dark:text-neutral-50">{page}</span> of{' '}
        <span className="font-medium text-neutral-900 dark:text-neutral-50">{totalPages}</span>
        {' · '}
        <span className="font-medium text-neutral-900 dark:text-neutral-50">{totalResults}</span>{' '}
        result{totalResults === 1 ? '' : 's'}
      </p>

      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" disabled={page <= 1} onClick={onPrevious}>
          Previous
        </Button>
        <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={onNext}>
          Next
        </Button>
      </div>
    </nav>
  )
}
