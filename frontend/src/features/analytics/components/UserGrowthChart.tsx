import { BaseAreaChart, BaseBarChart, BaseLineChart, seriesToChartPoints } from '@/components/charts'

import type { UserGrowthTrends } from '../types'
import AnalyticsChartCard from './AnalyticsChartCard'

export interface UserGrowthChartProps {
  trends: UserGrowthTrends
}

export default function UserGrowthChart({ trends }: UserGrowthChartProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <AnalyticsChartCard
        title="User Registrations"
        description="New accounts created during the selected period."
      >
        <BaseBarChart
          data={seriesToChartPoints(trends.user_registrations.points)}
          ariaLabel="User registrations trend"
          valueLabel="Registrations"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Active Users"
        description="Distinct users with platform activity."
      >
        <BaseAreaChart
          data={seriesToChartPoints(trends.active_users.points)}
          ariaLabel="Active users trend"
          valueLabel="Active users"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Login Activity"
        description="Successful authentication events."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.login_activity.points)}
          ariaLabel="Login activity trend"
          valueLabel="Logins"
        />
      </AnalyticsChartCard>

      <AnalyticsChartCard
        title="Questions Asked"
        description="Chat questions submitted by users."
      >
        <BaseLineChart
          data={seriesToChartPoints(trends.questions_asked.points)}
          ariaLabel="Questions asked trend"
          valueLabel="Questions"
        />
      </AnalyticsChartCard>
    </div>
  )
}
