import { BaseAreaChart, BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { ErrorTrends } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface ErrorTrendChartProps {
  trends: ErrorTrends
}

export default function ErrorTrendChart({ trends }: ErrorTrendChartProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="Total Errors"
        description="Failed operational events over time."
      >
        <BaseAreaChart
          data={seriesToChartPoints(trends.total_errors.points)}
          ariaLabel="Total errors trend"
          valueLabel="Errors"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Authentication Failures"
        description="Failed login attempts over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.authentication_failures.points)}
          ariaLabel="Authentication failure trend"
          valueLabel="Failures"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Retrieval Failures"
        description="Chat retrieval failures over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.retrieval_failures.points)}
          ariaLabel="Retrieval failure trend"
          valueLabel="Failures"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Permission Denials"
        description="Authorization failures over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.permission_denials.points)}
          ariaLabel="Permission denial trend"
          valueLabel="Denials"
        />
      </AnalyticsChartCard>
    </div>
  )
}
