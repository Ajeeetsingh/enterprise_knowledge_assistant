import Card from '@/components/ui/Card'

import AnalyticsKPICard from '../AnalyticsKPICard'
import type { AIAnalyticsOverview } from '../../types'
import { formatMetricValue } from '../../types'

export interface AIOverviewCardsProps {
  overview: AIAnalyticsOverview
}

function formatSeconds(value: number | null): string {
  if (value === null) {
    return 'N/A'
  }
  return `${formatMetricValue(value)}s`
}

export default function AIOverviewCards({ overview }: AIOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard label="Total AI Questions" value={overview.total_questions} />
      <AnalyticsKPICard label="Responses Generated" value={overview.responses_generated} />
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Avg Response Time
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {formatSeconds(overview.average_response_time_seconds)}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Avg Retrieved Documents
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {overview.average_retrieved_documents ?? 'N/A'}
        </p>
      </Card>
      <AnalyticsKPICard
        label="Citation Usage Rate"
        value={overview.citation_usage_rate}
        format="percent"
      />
      <AnalyticsKPICard
        label="Retrieval Success Rate"
        value={overview.retrieval_success_rate}
        format="percent"
      />
      <AnalyticsKPICard
        label="Retrieval Failure Rate"
        value={overview.retrieval_failure_rate}
        format="percent"
      />
      <AnalyticsKPICard label="AI Error Rate" value={overview.ai_error_rate} format="percent" />
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Avg Confidence Score
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {overview.average_confidence_score ?? 'N/A'}
        </p>
      </Card>
    </div>
  )
}
