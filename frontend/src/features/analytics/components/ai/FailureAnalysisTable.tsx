import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { FailureAnalysisItem } from '../../types'

export interface FailureAnalysisTableProps {
  items: FailureAnalysisItem[]
}

export default function FailureAnalysisTable({ items }: FailureAnalysisTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No failures recorded"
        description="No retrieval failures occurred during the selected period."
      />
    )
  }

  return (
    <DataTable caption="Failed retrieval analysis">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Reason</DataTableHeaderCell>
          <DataTableHeaderCell>Count</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {items.map((item) => (
          <DataTableRow key={item.reason}>
            <DataTableCell>{item.reason}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
