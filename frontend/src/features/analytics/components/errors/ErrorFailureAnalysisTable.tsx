import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { ErrorFrequencyItem } from '../../types'

export interface ErrorFailureAnalysisTableProps {
  operations: ErrorFrequencyItem[]
  retrievalFailures: ErrorFrequencyItem[]
}

export default function ErrorFailureAnalysisTable({
  operations,
  retrievalFailures,
}: ErrorFailureAnalysisTableProps) {
  const rows = [
    ...operations.map((item) => ({ ...item, section: 'Failed operation' as const })),
    ...retrievalFailures.map((item) => ({ ...item, section: 'Retrieval failure' as const })),
  ]

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No failure analysis data"
        description="No measurable failure patterns were found for the selected period."
      />
    )
  }

  return (
    <DataTable caption="Failure analysis">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Section</DataTableHeaderCell>
          <DataTableHeaderCell>Detail</DataTableHeaderCell>
          <DataTableHeaderCell>Category</DataTableHeaderCell>
          <DataTableHeaderCell>Count</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {rows.map((item) => (
          <DataTableRow key={`${item.section}-${item.label}-${item.category}`}>
            <DataTableCell muted>{item.section}</DataTableCell>
            <DataTableCell>{item.label}</DataTableCell>
            <DataTableCell muted>{item.category}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
