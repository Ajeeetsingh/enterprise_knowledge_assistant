import AnalyticsKPICard from '../AnalyticsKPICard'
import type { KnowledgeAnalyticsOverview } from '../../types'
import { formatMetricValue } from '../../types'

export interface KnowledgeOverviewCardsProps {
  overview: KnowledgeAnalyticsOverview
}

export default function KnowledgeOverviewCards({ overview }: KnowledgeOverviewCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <AnalyticsKPICard
        label="Total Documents"
        value={overview.total_documents}
        icon="documents"
        size="primary"
      />
      <AnalyticsKPICard
        label="Active Documents"
        value={overview.active_documents}
        icon="success"
        size="primary"
        tone="good"
      />
      <AnalyticsKPICard
        label="Stale Documents"
        value={overview.stale_documents}
        icon="documents"
        size="primary"
        tone="warn"
      />
      <AnalyticsKPICard
        label="Unused Documents"
        value={overview.unused_documents}
        icon="documents"
        size="primary"
        tone="bad"
      />
      <AnalyticsKPICard
        label="Avg Document Views"
        value={overview.average_document_views ?? null}
        format="text"
        icon="search"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Avg Citations per Document"
        value={overview.average_citations_per_document ?? null}
        format="text"
        icon="documents"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Search Success Rate"
        value={overview.search_success_rate}
        format="percent"
        icon="success"
        size="secondary"
      />
      <AnalyticsKPICard
        label="Reporting Window"
        value={`${new Date(overview.start_date).toLocaleDateString()} – ${new Date(overview.end_date).toLocaleDateString()}`}
        format="text"
        icon="reports"
        size="secondary"
        hint={`${formatMetricValue(overview.active_documents)} active of ${formatMetricValue(overview.total_documents)} total`}
      />
    </div>
  )
}
