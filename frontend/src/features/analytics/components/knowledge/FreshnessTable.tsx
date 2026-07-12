import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { FreshnessItem } from '../../types'

export interface FreshnessTableProps {
  recentUploads: FreshnessItem[]
  longestInactive: FreshnessItem[]
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString()
}

export default function FreshnessTable({
  recentUploads,
  longestInactive,
}: FreshnessTableProps) {
  const rows = [
    ...recentUploads.map((item) => ({ ...item, section: 'Recent upload' as const })),
    ...longestInactive.map((item) => ({ ...item, section: 'Longest inactive' as const })),
  ]

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No freshness data"
        description="No document freshness records are available for the selected period."
      />
    )
  }

  return (
    <DataTable caption="Content freshness">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Section</DataTableHeaderCell>
          <DataTableHeaderCell>Document</DataTableHeaderCell>
          <DataTableHeaderCell>Collection</DataTableHeaderCell>
          <DataTableHeaderCell>Uploaded</DataTableHeaderCell>
          <DataTableHeaderCell>Updated</DataTableHeaderCell>
          <DataTableHeaderCell>Days Inactive</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {rows.map((item) => (
          <DataTableRow key={`${item.section}-${item.document_id}`}>
            <DataTableCell muted>{item.section}</DataTableCell>
            <DataTableCell>{item.filename}</DataTableCell>
            <DataTableCell muted>{item.collection}</DataTableCell>
            <DataTableCell muted>{formatDate(item.uploaded_at)}</DataTableCell>
            <DataTableCell muted>{formatDate(item.updated_at)}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.days_inactive}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
