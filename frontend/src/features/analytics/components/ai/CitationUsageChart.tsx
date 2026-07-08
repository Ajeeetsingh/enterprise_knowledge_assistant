import { BaseBarChart, seriesToChartPoints } from '@/components/charts'

import type { AITrends } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface CitationUsageChartProps {
  trends: AITrends
}

export default function CitationUsageChart({ trends }: CitationUsageChartProps) {
  return (
    <AnalyticsChartCard
      title="Citation Usage"
      description="Responses with citations retrieved from the knowledge base."
    >
      <BaseBarChart
        data={seriesToChartPoints(trends.citation_usage.points)}
        ariaLabel="Citation usage trend"
        valueLabel="Cited responses"
      />
    </AnalyticsChartCard>
  )
}
