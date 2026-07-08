import { BaseAreaChart, BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { AITrends } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface RetrievalTrendChartProps {
  trends: AITrends
}

export default function RetrievalTrendChart({ trends }: RetrievalTrendChartProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="Retrieval Success Trend"
        description="Successful AI responses over time."
      >
        <BaseAreaChart
          data={seriesToChartPoints(trends.retrieval_success.points)}
          ariaLabel="Retrieval success trend"
          valueLabel="Successful responses"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Retrieval Failure Trend"
        description="Failed retrieval attempts over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.retrieval_failures.points)}
          ariaLabel="Retrieval failure trend"
          valueLabel="Failures"
        />
      </AnalyticsChartCard>
    </div>
  )
}
