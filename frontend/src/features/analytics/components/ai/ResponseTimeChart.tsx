import { BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { AITrends } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface ResponseTimeChartProps {
  trends: AITrends
}

export default function ResponseTimeChart({ trends }: ResponseTimeChartProps) {
  return (
    <AnalyticsChartCard
      title="Response Time Trend"
      description="Average assistant response latency by day."
    >
      <BaseLineChart
        data={seriesToChartPoints(trends.average_response_time.points)}
        ariaLabel="Average response time trend"
        valueLabel="Seconds"
      />
    </AnalyticsChartCard>
  )
}
