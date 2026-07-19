import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { AnalyticsExportButton } from '@/features/reports'
import { resolveErrorMessage } from '@/services/errorHandler'

import { AnalyticsDateFilter, AnalyticsErrorPanel } from '../components'
import {
  EndpointFailureTable,
  ErrorCategoryChart,
  ErrorOverviewCards,
  ErrorTrendChart,
  ErrorFailureAnalysisTable,
} from '../components/errors'
import { DEFAULT_DATE_RANGE_PRESET } from '../constants'
import {
  useEndpointFailures,
  useErrorAnalytics,
  useErrorCategories,
  useErrorTrends,
  useFailureAnalysis,
} from '../hooks'
import type { AnalyticsFilterParams } from '../types'

export default function ErrorAnalyticsPage() {
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

  const overviewQuery = useErrorAnalytics(queryFilters)
  const trendsQuery = useErrorTrends(queryFilters)
  const categoriesQuery = useErrorCategories(queryFilters)
  const endpointsQuery = useEndpointFailures({ ...queryFilters, limit: 10 })
  const failuresQuery = useFailureAnalysis({ ...queryFilters, limit: 10 })

  const queries = [overviewQuery, trendsQuery, categoriesQuery, endpointsQuery, failuresQuery]
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
            Error Analytics
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Operational failures, recurring error patterns, and endpoint analysis.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <AnalyticsExportButton module="errors" filters={queryFilters} />
          <Button
            variant="secondary"
            isLoading={isRefreshing && !isInitialLoading}
            disabled={isInitialLoading}
            aria-label="Refresh error analytics data"
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
          <Spinner size="lg" label="Loading error analytics data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading error analytics data…
          </p>
        </div>
      ) : null}

      {!isInitialLoading && hasError ? (
        <AnalyticsErrorPanel
          message={resolveErrorMessage(failedQuery?.error, 'Something went wrong. Please try again.')}
          isRetrying={isRefreshing}
          onRetry={handleRefresh}
        />
      ) : null}

      {!isInitialLoading && !hasError && overviewQuery.data ? (
        <>
          <section aria-labelledby="error-analytics-kpi-heading">
            <h3 id="error-analytics-kpi-heading" className="sr-only">
              Error analytics KPIs
            </h3>
            <ErrorOverviewCards overview={overviewQuery.data} />
          </section>

          {trendsQuery.data ? <ErrorTrendChart trends={trendsQuery.data} /> : null}

          {categoriesQuery.data ? <ErrorCategoryChart categories={categoriesQuery.data} /> : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Endpoint Failures
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Frequently failing endpoints derived from audit metadata.
                </p>
              </div>
              <EndpointFailureTable items={endpointsQuery.data?.items ?? []} />
            </Card>

            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Failure Analysis
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Most common failed operations and retrieval failure reasons.
                </p>
              </div>
              <ErrorFailureAnalysisTable
                operations={failuresQuery.data?.failed_operations ?? []}
                retrievalFailures={failuresQuery.data?.retrieval_failures ?? []}
              />
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
