import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { AnalyticsExportButton } from '@/features/reports'
import { resolveErrorMessage } from '@/services/errorHandler'

import { AnalyticsDateFilter, AnalyticsErrorPanel } from '../components'
import {
  CollectionUsageChart,
  DocumentUsageChart,
  FreshnessTable,
  KnowledgeGapTable,
  KnowledgeOverviewCards,
  SearchTrendChart,
  TopDocumentsTable,
} from '../components/knowledge'
import { DEFAULT_DATE_RANGE_PRESET } from '../constants'
import {
  useCollectionAnalytics,
  useDocumentAnalytics,
  useFreshnessAnalytics,
  useKnowledgeAnalytics,
  useKnowledgeGapAnalytics,
  useSearchAnalytics,
} from '../hooks'
import type { AnalyticsFilterParams } from '../types'

export default function KnowledgeAnalyticsPage() {
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

  const overviewQuery = useKnowledgeAnalytics(queryFilters)
  const documentsQuery = useDocumentAnalytics({ ...queryFilters, limit: 10 })
  const collectionsQuery = useCollectionAnalytics(queryFilters)
  const searchesQuery = useSearchAnalytics(queryFilters)
  const gapsQuery = useKnowledgeGapAnalytics({ ...queryFilters, limit: 10 })
  const freshnessQuery = useFreshnessAnalytics({ ...queryFilters, limit: 10 })

  const queries = [
    overviewQuery,
    documentsQuery,
    collectionsQuery,
    searchesQuery,
    gapsQuery,
    freshnessQuery,
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
            Knowledge Analytics
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Knowledge base health, usage, search behavior, and content freshness.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <AnalyticsExportButton module="knowledge" filters={queryFilters} />
          <Button
            variant="secondary"
            isLoading={isRefreshing && !isInitialLoading}
            disabled={isInitialLoading}
            aria-label="Refresh knowledge analytics data"
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
          <Spinner size="lg" label="Loading knowledge analytics data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading knowledge analytics data…
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
          <section aria-labelledby="knowledge-analytics-kpi-heading">
            <h3 id="knowledge-analytics-kpi-heading" className="sr-only">
              Knowledge analytics KPIs
            </h3>
            <KnowledgeOverviewCards overview={overviewQuery.data} />
          </section>

          <div className="grid gap-4 xl:grid-cols-2">
            {documentsQuery.data ? <DocumentUsageChart documents={documentsQuery.data} /> : null}
            {collectionsQuery.data ? (
              <CollectionUsageChart collections={collectionsQuery.data} />
            ) : null}
          </div>

          {searchesQuery.data ? <SearchTrendChart searches={searchesQuery.data} /> : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Top Documents
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Most cited documents during the selected period.
                </p>
              </div>
              <TopDocumentsTable items={documentsQuery.data?.most_viewed ?? []} />
            </Card>

            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Knowledge Gaps
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Measurable gaps including uncited documents and failed searches.
                </p>
              </div>
              <KnowledgeGapTable items={gapsQuery.data?.items ?? []} />
            </Card>
          </div>

          <Card className="flex flex-col gap-4">
            <div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                Content Freshness
              </h3>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                Recent uploads and longest inactive documents.
              </p>
            </div>
            <FreshnessTable
              recentUploads={freshnessQuery.data?.recent_uploads ?? []}
              longestInactive={freshnessQuery.data?.longest_inactive ?? []}
            />
          </Card>
        </>
      ) : null}
    </div>
  )
}
