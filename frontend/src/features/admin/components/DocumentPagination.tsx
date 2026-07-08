import Button from '@/components/ui/Button'

export interface DocumentPaginationProps {
  page: number
  totalPages: number
  totalResults: number
  onPrevious: () => void
  onNext: () => void
}

export default function DocumentPagination({
  page,
  totalPages,
  totalResults,
  onPrevious,
  onNext,
}: DocumentPaginationProps) {
  return (
    <nav
      aria-label="Document pagination"
      className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-neutral-600 dark:text-neutral-300">
        Page <span className="font-medium">{page}</span> of{' '}
        <span className="font-medium">{totalPages}</span>
        {' · '}
        <span className="font-medium">{totalResults}</span> result
        {totalResults === 1 ? '' : 's'}
      </p>

      <div className="flex gap-2">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={onPrevious}>
          Previous
        </Button>
        <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={onNext}>
          Next
        </Button>
      </div>
    </nav>
  )
}
