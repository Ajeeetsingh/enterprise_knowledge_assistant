import Card from '@/components/ui/Card'

import AnalyticsKPICard from '../AnalyticsKPICard'
import type { ErrorAnalyticsOverview } from '../../types'
import { formatPercentValue } from '../../types'

export interface ErrorOverviewCardsProps {
  overview: ErrorAnalyticsOverview
}

function formatOptionalCount(value: number | null): string {
  return value === null ? 'N/A' : String(value)
}

export default function ErrorOverviewCards({ overview }: ErrorOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard label="Total Errors" value={overview.total_errors} />
      <AnalyticsKPICard label="Authentication Failures" value={overview.authentication_failures} />
      <AnalyticsKPICard label="Authorization Failures" value={overview.authorization_failures} />
      <AnalyticsKPICard label="Retrieval Failures" value={overview.retrieval_failures} />
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Upload Failures</p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatOptionalCount(overview.upload_failures)}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Indexing Failures
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatOptionalCount(overview.indexing_failures)}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">API Errors</p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatOptionalCount(overview.api_errors)}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Background Job Failures
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatOptionalCount(overview.background_job_failures)}
        </p>
      </Card>
      <AnalyticsKPICard label="Error Rate" value={overview.error_rate} format="percent" />
      <AnalyticsKPICard
        label="Error-Free Requests"
        value={overview.error_free_requests_percentage}
        format="percent"
      />
      <Card className="sm:col-span-2">
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Reporting Window
        </p>
        <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-200">
          {new Date(overview.start_date).toLocaleDateString()} –{' '}
          {new Date(overview.end_date).toLocaleDateString()}
        </p>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          Error rate {formatPercentValue(overview.error_rate)} across audited operations
        </p>
      </Card>
    </div>
  )
}
