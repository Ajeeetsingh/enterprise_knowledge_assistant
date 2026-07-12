import EmptyState from '@/components/ui/EmptyState'
import DataTable, {
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeaderCell,
  DataTableRow,
} from '@/components/ui/DataTable'

import type { QuestionFrequencyItem } from '../../types'

export interface TopQuestionsTableProps {
  items: QuestionFrequencyItem[]
}

export default function TopQuestionsTable({ items }: TopQuestionsTableProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No questions recorded"
        description="No user questions were captured during the selected period."
      />
    )
  }

  return (
    <DataTable caption="Top user questions">
      <DataTableHead>
        <DataTableRow interactive={false}>
          <DataTableHeaderCell>Question</DataTableHeaderCell>
          <DataTableHeaderCell>Count</DataTableHeaderCell>
        </DataTableRow>
      </DataTableHead>
      <DataTableBody>
        {items.map((item) => (
          <DataTableRow key={item.question}>
            <DataTableCell>{item.question}</DataTableCell>
            <DataTableCell className="tabular-nums">{item.count}</DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
