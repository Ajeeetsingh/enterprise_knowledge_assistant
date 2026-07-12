import AnalyticsKPICard from '../AnalyticsKPICard'
import type { ErrorAnalyticsOverview } from '../../types'
import { formatPercentValue } from '../../types'

export interface ErrorOverviewCardsProps {
  overview: ErrorAnalyticsOverview
}

export default function ErrorOverviewCards({ overview }: ErrorOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard
        label="Total Errors"
        value={overview.total_errors}
        icon="errors"
        size="primary"
        tone="bad"
      />
      <AnalyticsKPICard
        label="Authentication Failures"
        value={overview.authentication_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Authorization Failures"
        value={overview.authorization_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Retrieval Failures"
        value={overview.retrieval_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Upload Failures"
        value={overview.upload_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Indexing Failures"
        value={overview.indexing_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="API Errors"
        value={overview.api_errors}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Background Job Failures"
        value={overview.background_job_failures}
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Error Rate"
        value={overview.error_rate}
        format="percent"
        icon="errors"
        size="secondary"
        tone="bad"
      />
      <AnalyticsKPICard
        label="Error-Free Requests"
        value={overview.error_free_requests_percentage}
        format="percent"
        icon="success"
        size="secondary"
        tone="good"
      />
      <AnalyticsKPICard
        className="sm:col-span-2"
        label="Reporting Window"
        value={`${new Date(overview.start_date).toLocaleDateString()} – ${new Date(overview.end_date).toLocaleDateString()}`}
        format="text"
        icon="reports"
        size="secondary"
        hint={`Error rate ${formatPercentValue(overview.error_rate)} across audited operations`}
      />
    </div>
  )
}
