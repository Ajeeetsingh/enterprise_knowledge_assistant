import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

export interface AnalyticsErrorPanelProps {
  message: string
  isRetrying?: boolean
  onRetry: () => void
}

export default function AnalyticsErrorPanel({
  message,
  isRetrying = false,
  onRetry,
}: AnalyticsErrorPanelProps) {
  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div role="alert">
          <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">
            Unable to load analytics
          </h3>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{message}</p>
        </div>
        <Button variant="secondary" isLoading={isRetrying} onClick={onRetry}>
          Retry
        </Button>
      </div>
    </Card>
  )
}
