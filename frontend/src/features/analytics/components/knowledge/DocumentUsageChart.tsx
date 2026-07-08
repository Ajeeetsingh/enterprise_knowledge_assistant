import { BaseAreaChart, seriesToChartPoints } from '@/components/charts'

import type { DocumentAnalytics } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface DocumentUsageChartProps {
  documents: DocumentAnalytics
}

export default function DocumentUsageChart({ documents }: DocumentUsageChartProps) {
  return (
    <AnalyticsChartCard
      title="Document Usage"
      description="Cited documents over time for the selected period."
    >
      <BaseAreaChart
        data={seriesToChartPoints(documents.document_usage_trend.points)}
        ariaLabel="Document usage trend"
        valueLabel="Citations"
      />
    </AnalyticsChartCard>
  )
}
