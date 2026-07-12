import Button from '@/components/ui/Button'

export interface UserPaginationProps {
  page: number
  totalPages: number
  totalResults: number
  onPrevious: () => void
  onNext: () => void
}

export default function UserPagination({
  page,
  totalPages,
  totalResults,
  onPrevious,
  onNext,
}: UserPaginationProps) {
  return (
    <nav
      aria-label="User pagination"
      className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="pagination-meta">
        Page <span className="font-medium text-foreground">{page}</span> of{' '}
        <span className="font-medium text-foreground">{totalPages}</span>
        {' · '}
        <span className="font-medium text-foreground">{totalResults}</span> result
        {totalResults === 1 ? '' : 's'}
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
