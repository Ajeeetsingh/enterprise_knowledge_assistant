import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { EndpointFailureItem } from '../../types'

export interface EndpointFailureTableProps {
  items: EndpointFailureItem[]
}

export default function EndpointFailureTable({ items }: EndpointFailureTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No endpoint failures recorded"
        description="No endpoint or resource failures were captured during the selected period."
      />
    )
  }

  return (
    <DataTable caption="Endpoint failure analysis">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Endpoint</DataTableHeaderCell>
          <DataTableHeaderCell>Service</DataTableHeaderCell>
          <DataTableHeaderCell>Count</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {items.map((item) => (
          <DataTableRow key={`${item.service}-${item.endpoint}`}>
            <DataTableCell>{item.endpoint}</DataTableCell>
            <DataTableCell muted>{item.service}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
