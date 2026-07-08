import Card from '@/components/ui/Card'

import AnalyticsKPICard from '../AnalyticsKPICard'
import type { KnowledgeAnalyticsOverview } from '../../types'
import { formatMetricValue } from '../../types'

export interface KnowledgeOverviewCardsProps {
  overview: KnowledgeAnalyticsOverview
}

export default function KnowledgeOverviewCards({ overview }: KnowledgeOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard label="Total Documents" value={overview.total_documents} />
      <AnalyticsKPICard label="Active Documents" value={overview.active_documents} />
      <AnalyticsKPICard label="Stale Documents" value={overview.stale_documents} />
      <AnalyticsKPICard label="Unused Documents" value={overview.unused_documents} />
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Avg Document Views
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {overview.average_document_views ?? 'N/A'}
        </p>
      </Card>
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Avg Citations per Document
        </p>
        <p className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
          {overview.average_citations_per_document ?? 'N/A'}
        </p>
      </Card>
      <AnalyticsKPICard
        label="Search Success Rate"
        value={overview.search_success_rate}
        format="percent"
      />
      <Card>
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          Reporting Window
        </p>
        <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-200">
          {new Date(overview.start_date).toLocaleDateString()} –{' '}
          {new Date(overview.end_date).toLocaleDateString()}
        </p>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          {formatMetricValue(overview.active_documents)} active of{' '}
          {formatMetricValue(overview.total_documents)} total
        </p>
      </Card>
    </div>
  )
}
