import AnalyticsKPICard from '../AnalyticsKPICard'
import type { AIAnalyticsOverview } from '../../types'
import { formatMetricValue } from '../../types'

export interface AIOverviewCardsProps {
  overview: AIAnalyticsOverview
}

export default function AIOverviewCards({ overview }: AIOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard
        label="Total AI Questions"
        value={overview.total_questions}
        icon="ai"
        size="primary"
      />
      <AnalyticsKPICard
        label="Responses Generated"
        value={overview.responses_generated}
        icon="success"
        size="primary"
      />
      <AnalyticsKPICard
        label="Avg Response Time"
        value={
          overview.average_response_time_seconds === null
            ? null
            : `${formatMetricValue(overview.average_response_time_seconds)}s`
        }
        format="text"
        icon="time"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Avg Retrieved Documents"
        value={overview.average_retrieved_documents ?? null}
        format="text"
        icon="documents"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Citation Usage Rate"
        value={overview.citation_usage_rate}
        format="percent"
        icon="success"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Retrieval Success Rate"
        value={overview.retrieval_success_rate}
        format="percent"
        icon="success"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Retrieval Failure Rate"
        value={overview.retrieval_failure_rate}
        format="percent"
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="AI Error Rate"
        value={overview.ai_error_rate}
        format="percent"
        icon="errors"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Avg Confidence Score"
        value={overview.average_confidence_score ?? null}
        format="text"
        icon="ai"
        size="secondary"
      />
    </div>
  )
}
