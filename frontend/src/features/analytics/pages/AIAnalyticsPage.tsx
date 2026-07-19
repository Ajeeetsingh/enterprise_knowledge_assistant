import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { AnalyticsExportButton } from '@/features/reports'
import { resolveErrorMessage } from '@/services/errorHandler'

import {
  AIOverviewCards,
  CitationUsageChart,
  FailureAnalysisTable,
  ResponseTimeChart,
  RetrievalTrendChart,
  TopQuestionsTable,
} from '../components/ai'
import { AnalyticsDateFilter, AnalyticsErrorPanel } from '../components'
import { DEFAULT_DATE_RANGE_PRESET } from '../constants'
import {
  useAIAnalytics,
  useAITrends,
  useFailureAnalytics,
  useRetrievalAnalytics,
  useTopQuestions,
} from '../hooks'
import type { AnalyticsFilterParams } from '../types'

export default function AIAnalyticsPage() {
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

  const overviewQuery = useAIAnalytics(queryFilters)
  const trendsQuery = useAITrends(queryFilters)
  const retrievalQuery = useRetrievalAnalytics(queryFilters)
  const questionsQuery = useTopQuestions({ ...queryFilters, limit: 10 })
  const failuresQuery = useFailureAnalytics({ ...queryFilters, limit: 10 })

  const queries = [overviewQuery, trendsQuery, retrievalQuery, questionsQuery, failuresQuery]
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
            AI Analytics
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            AI performance, retrieval quality, and assistant effectiveness.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <AnalyticsExportButton module="ai" filters={queryFilters} />
          <Button
            variant="secondary"
            isLoading={isRefreshing && !isInitialLoading}
            disabled={isInitialLoading}
            aria-label="Refresh AI analytics data"
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
          <Spinner size="lg" label="Loading AI analytics data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading AI analytics data…
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
          <section aria-labelledby="ai-analytics-kpi-heading">
            <h3 id="ai-analytics-kpi-heading" className="sr-only">
              AI analytics KPIs
            </h3>
            <AIOverviewCards overview={overviewQuery.data} />
          </section>

          {trendsQuery.data ? (
            <>
              <ResponseTimeChart trends={trendsQuery.data} />
              <RetrievalTrendChart trends={trendsQuery.data} />
              <CitationUsageChart trends={trendsQuery.data} />
            </>
          ) : null}

          {retrievalQuery.data ? (
            <Card className="flex flex-col gap-2">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                Retrieval Summary
              </h3>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {retrievalQuery.data.empty_retrievals} empty retrievals ·{' '}
                {retrievalQuery.data.retrieval_success_percentage}% success rate
              </p>
            </Card>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Top Questions
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  {questionsQuery.data?.quality_summary ?? 'Most common user questions.'}
                </p>
              </div>
              <TopQuestionsTable items={questionsQuery.data?.items ?? []} />
            </Card>

            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Failed Retrievals
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Aggregated failure reasons for the selected period.
                </p>
              </div>
              <FailureAnalysisTable items={failuresQuery.data?.items ?? []} />
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
