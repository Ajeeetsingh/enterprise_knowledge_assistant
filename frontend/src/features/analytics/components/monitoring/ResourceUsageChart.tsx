import { BaseBarChart } from '@/components/charts'
import PlaceholderState from '@/components/ui/PlaceholderState'

import type { ResourceMetrics } from '../../types'
import { formatBytes } from '../../types'
import AnalyticsChartCard from '../AnalyticsChartCard'

export interface ResourceUsageChartProps {
  resources: ResourceMetrics
}

export default function ResourceUsageChart({ resources }: ResourceUsageChartProps) {
  const data = [
    { label: 'Documents', value: resources.total_documents },
    { label: 'Users', value: resources.total_users },
    { label: 'Conversations', value: resources.total_conversations },
    { label: 'Files', value: resources.uploaded_file_count },
  ]

  return (
    <AnalyticsChartCard
      title="Resource Usage"
      description={`Storage usage: ${formatBytes(resources.storage_usage_bytes)}`}
    >
      <BaseBarChart data={data} ariaLabel="Resource usage chart" valueLabel="Count" />
      {resources.vector_index_size_bytes === null ? (
        <PlaceholderState className="mt-3">
          Background workers and vector index size are not instrumented in this release.
        </PlaceholderState>
      ) : (
        <p className="mt-3 text-xs text-muted">
          Vector index: {formatBytes(resources.vector_index_size_bytes)}
        </p>
      )}
    </AnalyticsChartCard>
  )
}
