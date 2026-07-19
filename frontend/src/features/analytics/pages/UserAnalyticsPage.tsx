import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { AnalyticsExportButton } from '@/features/reports'
import { resolveErrorMessage } from '@/services/errorHandler'

import {
  ActivityTrendChart,
  AnalyticsDateFilter,
  AnalyticsErrorPanel,
  AnalyticsKPICard,
  InactiveUsersTable,
  TopUsersTable,
  UserGrowthChart,
} from '../components'
import { DEFAULT_DATE_RANGE_PRESET } from '../constants'
import {
  useActivityTrend,
  useInactiveUsers,
  useTopUsers,
  useUserAnalytics,
  useUserGrowth,
} from '../hooks'
import type { AnalyticsFilterParams } from '../types'

export default function UserAnalyticsPage() {
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

  const overviewQuery = useUserAnalytics(queryFilters)
  const growthQuery = useUserGrowth(queryFilters)
  const activityQuery = useActivityTrend(queryFilters)
  const topUsersQuery = useTopUsers({ ...queryFilters, limit: 10 })
  const inactiveUsersQuery = useInactiveUsers({ ...queryFilters, limit: 10 })

  const queries = [overviewQuery, growthQuery, activityQuery, topUsersQuery, inactiveUsersQuery]
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
            User Analytics
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Adoption, engagement, and activity insights for administrators.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <AnalyticsExportButton module="user" filters={queryFilters} />
          <Button
            variant="secondary"
            isLoading={isRefreshing && !isInitialLoading}
            disabled={isInitialLoading}
            aria-label="Refresh analytics data"
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
          <Spinner size="lg" label="Loading analytics data" />
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Loading analytics data…
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
          <section aria-labelledby="user-analytics-kpi-heading">
            <h3 id="user-analytics-kpi-heading" className="sr-only">
              User analytics KPIs
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <AnalyticsKPICard
                label="Total Users"
                value={overviewQuery.data.total_users}
                icon="users"
                size="primary"
              />
              <AnalyticsKPICard
                label="New Users"
                value={overviewQuery.data.new_users}
                icon="users"
                size="primary"
              />
              <AnalyticsKPICard
                label="Daily Active Users"
                value={overviewQuery.data.daily_active_users}
                icon="users"
                size="primary"
              />
              <AnalyticsKPICard
                label="Weekly Active Users"
                value={overviewQuery.data.weekly_active_users}
                icon="users"
                size="primary"
              />
              <AnalyticsKPICard
                label="Monthly Active Users"
                value={overviewQuery.data.monthly_active_users}
                icon="users"
                size="secondary"
              />
              <AnalyticsKPICard
                label="Active User %"
                value={overviewQuery.data.active_user_percentage}
                format="percent"
                icon="success"
                size="secondary"
              />
              <AnalyticsKPICard
                label="Avg Conversations / User"
                value={overviewQuery.data.average_conversations_per_user}
                format="decimal"
                icon="ai"
                size="secondary"
              />
              <AnalyticsKPICard
                label="Avg Questions / User"
                value={overviewQuery.data.average_questions_per_user}
                format="decimal"
                icon="ai"
                size="secondary"
              />
            </div>
          </section>

          {growthQuery.data ? <UserGrowthChart trends={growthQuery.data} /> : null}

          {activityQuery.data ? <ActivityTrendChart activity={activityQuery.data} /> : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Top Active Users
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Users with the highest question activity in the selected period.
                </p>
              </div>
              <TopUsersTable users={topUsersQuery.data?.items ?? []} />
            </Card>

            <Card className="flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  Inactive Users
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  Active accounts with no recorded activity during the selected period.
                </p>
              </div>
              <InactiveUsersTable users={inactiveUsersQuery.data?.items ?? []} />
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
