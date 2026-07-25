import AnalyticsKPICard from '@/features/analytics/components/AnalyticsKPICard'
import Skeleton from '@/components/ui/Skeleton'
import { cn } from '@/utils/cn'

import type { WorkspaceSummary } from '../types'

export interface DashboardStatsRowProps {
  summary: WorkspaceSummary | undefined
  isLoading: boolean
}

const STAT_ACCENTS = {
  documents: 'dashboard-stat-card--indigo',
  conversations: 'dashboard-stat-card--purple',
  questions: 'dashboard-stat-card--sky',
  collections: 'dashboard-stat-card--amber',
} as const

export default function DashboardStatsRow({ summary, isLoading }: DashboardStatsRowProps) {
  if (isLoading || !summary) {
    return (
      <div
        className="grid grid-cols-2 gap-3 md:grid-cols-4"
        aria-busy="true"
        aria-label="Loading workspace stats"
      >
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="metric-card dashboard-stat-card space-y-3">
            <Skeleton className="h-3 w-24" variant="text" />
            <Skeleton className="h-7 w-14" />
          </div>
        ))}
      </div>
    )
  }

  const cards = [
    {
      label: 'Documents available',
      value: summary.documents_available,
      icon: 'documents' as const,
      accent: STAT_ACCENTS.documents,
    },
    {
      label: 'Conversations',
      value: summary.conversations,
      icon: 'ai' as const,
      accent: STAT_ACCENTS.conversations,
    },
    {
      label: 'Questions asked',
      value: summary.questions_asked,
      icon: 'search' as const,
      accent: STAT_ACCENTS.questions,
    },
    {
      label: 'Collections',
      value: summary.collections,
      icon: 'collections' as const,
      accent: STAT_ACCENTS.collections,
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cards.map((card) => (
        <AnalyticsKPICard
          key={card.label}
          label={card.label}
          value={card.value}
          icon={card.icon}
          size="secondary"
          className={cn('!p-4 dashboard-stat-card', card.accent)}
        />
      ))}
    </div>
  )
}
