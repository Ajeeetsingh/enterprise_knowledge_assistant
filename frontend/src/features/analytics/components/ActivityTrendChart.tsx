import { BaseAreaChart, BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { UserActivityAnalytics } from '../types'
import AnalyticsChartCard from './AnalyticsChartCard'

export interface ActivityTrendChartProps {
  activity: UserActivityAnalytics
}

export default function ActivityTrendChart({ activity }: ActivityTrendChartProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="Activity Trend"
        description="Distinct active users over time."
      >
        <BaseAreaChart
          data={seriesToChartPoints(activity.active_users.points)}
          ariaLabel="User activity trend"
          valueLabel="Active users"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Question Volume"
        description="Questions asked over time."
      >
        <BaseLineChart
          data={seriesToChartPoints(activity.questions_asked.points)}
          ariaLabel="Question volume trend"
          valueLabel="Questions"
        />
      </AnalyticsChartCard>
    </div>
  )
}
