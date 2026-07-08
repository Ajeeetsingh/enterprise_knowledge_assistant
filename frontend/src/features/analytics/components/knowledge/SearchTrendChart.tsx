import { BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { SearchAnalytics } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface SearchTrendChartProps {
  searches: SearchAnalytics
}

export default function SearchTrendChart({ searches }: SearchTrendChartProps) {
  return (
    <AnalyticsChartCard
      title="Search Trend"
      description="User search volume over time."
    >
      <BaseLineChart
        data={seriesToChartPoints(searches.search_trend.points)}
        ariaLabel="Search trend chart"
        valueLabel="Searches"
      />
    </AnalyticsChartCard>
  )
}
