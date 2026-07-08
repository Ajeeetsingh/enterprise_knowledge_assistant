import { BaseBarChart, seriesToChartPoints } from '@/components/charts'

import type { ErrorCategoryAnalytics } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface ErrorCategoryChartProps {
  categories: ErrorCategoryAnalytics
}

export default function ErrorCategoryChart({ categories }: ErrorCategoryChartProps) {
  const categoryData = seriesToChartPoints(categories.by_category)
  const serviceData = seriesToChartPoints(categories.by_service)

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="Errors by Category"
        description="Failed events grouped by audit category."
      >
        <BaseBarChart
          data={categoryData}
          ariaLabel="Errors by category chart"
          valueLabel="Errors"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Errors by Service"
        description="Failed events grouped by platform service."
      >
        <BaseBarChart
          data={serviceData}
          ariaLabel="Errors by service chart"
          valueLabel="Errors"
        />
      </AnalyticsChartCard>
    </div>
  )
}
