import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { KnowledgeGapItem } from '../../types'

const CATEGORY_LABELS: Record<string, string> = {
  questions_without_documents: 'No documents retrieved',
  failed_search: 'Failed search',
  never_cited_document: 'Never cited',
  never_searched_document: 'Never searched',
  low_engagement_collection: 'Low engagement collection',
}

export interface KnowledgeGapTableProps {
  items: KnowledgeGapItem[]
}

export default function KnowledgeGapTable({ items }: KnowledgeGapTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No knowledge gaps detected"
        description="No measurable knowledge gaps were found for the selected period."
      />
    )
  }

  return (
    <DataTable caption="Knowledge gap analysis">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Category</DataTableHeaderCell>
          <DataTableHeaderCell>Detail</DataTableHeaderCell>
          <DataTableHeaderCell>Count</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {items.map((item) => (
          <DataTableRow key={`${item.category}-${item.label}`}>
            <DataTableCell muted>{CATEGORY_LABELS[item.category] ?? item.category}</DataTableCell>
            <DataTableCell>{item.label}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
