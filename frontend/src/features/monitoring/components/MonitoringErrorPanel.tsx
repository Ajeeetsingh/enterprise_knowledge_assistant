import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

export interface MonitoringErrorPanelProps {
  message: string
  isRetrying: boolean
  onRetry: () => void
}

export default function MonitoringErrorPanel({
  message,
  isRetrying,
  onRetry,
}: MonitoringErrorPanelProps) {
  return (
    <Card>
      <div
        role="alert"
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h2 className="text-base font-semibold text-error-700 dark:text-error-400">
            Unable to load monitoring data
          </h2>
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{message}</p>
        </div>
        <Button
          variant="secondary"
          isLoading={isRetrying}
          disabled={isRetrying}
          onClick={onRetry}
        >
          Retry
        </Button>
      </div>
    </Card>
  )
}
