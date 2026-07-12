import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { DocumentUsageItem } from '../../types'

export interface TopDocumentsTableProps {
  items: DocumentUsageItem[]
}

export default function TopDocumentsTable({ items }: TopDocumentsTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No document usage recorded"
        description="No documents were cited during the selected period."
      />
    )
  }

  return (
    <DataTable caption="Top documents by citation usage">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Document</DataTableHeaderCell>
          <DataTableHeaderCell>Collection</DataTableHeaderCell>
          <DataTableHeaderCell>Views</DataTableHeaderCell>
          <DataTableHeaderCell>Citations</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {items.map((item) => (
          <DataTableRow key={item.document_id}>
            <DataTableCell>{item.filename}</DataTableCell>
            <DataTableCell muted>{item.collection}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.view_count}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.citation_count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
