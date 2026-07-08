import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import {
  MonitoringErrorPanel,
  SummaryMetricsGrid,
  SystemMetricsPanel,
} from '@/features/monitoring/components'
import { useMonitoringSummary } from '@/features/monitoring/hooks/useMonitoringSummary'
import { useSystemMetrics } from '@/features/monitoring/hooks/useSystemMetrics'
import type { ApiError } from '@/types'

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

export default function MonitoringPage() {
  const summaryQuery = useMonitoringSummary()
  const metricsQuery = useSystemMetrics()

  const isInitialLoading =
    (summaryQuery.isLoading && !summaryQuery.data) ||
    (metricsQuery.isLoading && !metricsQuery.data)

  const isRefreshing = summaryQuery.isFetching || metricsQuery.isFetching
  const hasError = summaryQuery.isError || metricsQuery.isError

  const errorMessage = summaryQuery.isError
    ? resolveErrorMessage(summaryQuery.error)
    : metricsQuery.isError
      ? resolveErrorMessage(metricsQuery.error)
      : 'Failed to load monitoring data.'

  function handleRefresh() {
    void summaryQuery.refetch()
    void metricsQuery.refetch()
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            Monitoring
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Platform activity, inventory counts, and system health.
          </p>
        </div>

        <Button
          variant="secondary"
          isLoading={isRefreshing && !isInitialLoading}
          disabled={isInitialLoading}
          aria-label="Refresh monitoring data"
          onClick={handleRefresh}
        >
          Refresh
        </Button>
      </div>

      {isInitialLoading && (
        <div
          className="flex flex-col items-center justify-center gap-3 py-16"
          role="status"
          aria-live="polite"
        >
          <Spinner size="lg" label="Loading monitoring data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading monitoring data…
          </p>
        </div>
      )}

      {!isInitialLoading && hasError && (
        <MonitoringErrorPanel
          message={errorMessage}
          isRetrying={isRefreshing}
          onRetry={handleRefresh}
        />
      )}

      {!isInitialLoading && !hasError && summaryQuery.data && (
        <SummaryMetricsGrid summary={summaryQuery.data} />
      )}

      {!isInitialLoading && !hasError && metricsQuery.data && (
        <SystemMetricsPanel metrics={metricsQuery.data} />
      )}
    </div>
  )
}
