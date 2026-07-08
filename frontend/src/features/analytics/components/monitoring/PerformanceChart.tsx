import { BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { MonitoringTrends } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface PerformanceChartProps {
  trends: MonitoringTrends
}

export default function PerformanceChart({ trends }: PerformanceChartProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="Search Latency Trend"
        description="Estimated chat turn latency by day when message pairs exist."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.search_latency.points)}
          ariaLabel="Search latency trend"
          valueLabel="Seconds"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Error Trend"
        description="Failed operational events over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.errors.points)}
          ariaLabel="Error trend"
          valueLabel="Errors"
        />
      </AnalyticsChartCard>
    </div>
  )
}
