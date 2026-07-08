import { BaseBarChart, seriesToChartPoints } from '@/components/charts'

import type { CollectionAnalytics } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface CollectionUsageChartProps {
  collections: CollectionAnalytics
}

export default function CollectionUsageChart({ collections }: CollectionUsageChartProps) {
  return (
    <AnalyticsChartCard
      title="Collection Usage"
      description="Citation activity grouped by collection."
    >
      <BaseBarChart
        data={seriesToChartPoints(collections.collection_popularity)}
        ariaLabel="Collection usage chart"
        valueLabel="Citations"
      />
    </AnalyticsChartCard>
  )
}
