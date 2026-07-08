import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { AnalyticsExportButton } from '@/features/reports'
import type { ApiError } from '@/types'

import { AnalyticsDateFilter, AnalyticsErrorPanel } from '../components'
import {
  HealthTimeline,
  PerformanceChart,
  ResourceUsageChart,
  ServiceStatusTable,
  SystemHealthCards,
} from '../components/monitoring'
import { DEFAULT_DATE_RANGE_PRESET } from '../constants'
import {
  useHealthTimeline,
  useMonitoringTrends,
  usePerformanceMetrics,
  useResourceMetrics,
  useServiceStatus,
  useSystemMonitoring,
} from '../hooks'
import type { AnalyticsFilterParams } from '../types'

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

function formatSeconds(value: number | null): string {
  return value === null ? 'N/A' : `${value}s`
}

export default function SystemMonitoringPage() {
  const [filters, setFilters] = useState<AnalyticsFilterParams>({
    range_preset: DEFAULT_DATE_RANGE_PRESET,
  })

  const queryFilters = useMemo(() => {
    if (filters.range_preset === 'custom') {
      return filters
    }
    return {
      range_preset: filters.range_preset ?? DEFAULT_DATE_RANGE_PRESET,
    }
  }, [filters])

  const overviewQuery = useSystemMonitoring(queryFilters)
  const performanceQuery = usePerformanceMetrics(queryFilters)
  const resourcesQuery = useResourceMetrics(queryFilters)
  const servicesQuery = useServiceStatus(queryFilters)
  const trendsQuery = useMonitoringTrends({ ...queryFilters, limit: 10 })
  const timelineQuery = useHealthTimeline({ ...queryFilters, limit: 10 })

  const queries = [
    overviewQuery,
    performanceQuery,
    resourcesQuery,
    servicesQuery,
    trendsQuery,
    timelineQuery,
  ]
  const isInitialLoading = queries.some((query) => query.isLoading && !query.data)
  const isRefreshing = queries.some((query) => query.isFetching)
  const failedQuery = queries.find((query) => query.isError)
  const hasError = Boolean(failedQuery)

  function handleRefresh() {
    queries.forEach((query) => {
      void query.refetch()
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            System Monitoring
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Operational health, performance, resources, and service status.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <AnalyticsExportButton module="monitoring" filters={queryFilters} />
          <Button
            variant="secondary"
            isLoading={isRefreshing && !isInitialLoading}
            disabled={isInitialLoading}
            aria-label="Refresh system monitoring data"
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </div>
      </div>

      <AnalyticsDateFilter filters={filters} onChange={setFilters} />

      {isInitialLoading ? (
        <div
          className="flex flex-col items-center justify-center gap-3 py-16"
          role="status"
          aria-live="polite"
        >
          <Spinner size="lg" label="Loading system monitoring data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading system monitoring data…
          </p>
        </div>
      ) : null}

      {!isInitialLoading && hasError ? (
        <AnalyticsErrorPanel
          message={resolveErrorMessage(failedQuery?.error)}
          isRetrying={isRefreshing}
          onRetry={handleRefresh}
        />
      ) : null}

      {!isInitialLoading && !hasError && overviewQuery.data ? (
        <>
          <section aria-labelledby="system-health-heading">
            <h3 id="system-health-heading" className="sr-only">
              System health KPIs
            </h3>
            <SystemHealthCards overview={overviewQuery.data} />
          </section>

          {performanceQuery.data ? (
            <Card className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Avg API Response</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">
                  {formatSeconds(performanceQuery.data.average_api_response_time_seconds)}
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Avg Search Time</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">
                  {formatSeconds(performanceQuery.data.average_search_time_seconds)}
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Avg Retrieval</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">
                  {formatSeconds(performanceQuery.data.average_retrieval_time_seconds)}
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">DB Query Time</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">
                  {formatSeconds(performanceQuery.data.database_query_time_seconds)}
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Embedding Time</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">
                  {formatSeconds(performanceQuery.data.embedding_generation_time_seconds)}
                </p>
              </div>
            </Card>
          ) : null}

          {trendsQuery.data ? <PerformanceChart trends={trendsQuery.data} /> : null}

          {resourcesQuery.data ? <ResourceUsageChart resources={resourcesQuery.data} /> : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Service Status
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Current health probes for platform services.
                </p>
              </div>
              <ServiceStatusTable items={servicesQuery.data?.items ?? []} />
            </Card>

            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Health Timeline
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Recent operational health events from audit records.
                </p>
              </div>
              <HealthTimeline items={timelineQuery.data?.items ?? []} />
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
