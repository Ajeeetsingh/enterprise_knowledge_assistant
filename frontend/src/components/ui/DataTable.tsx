import { type ReactNode } from 'react'

import { cn } from '@/utils/cn'

export interface DataTableProps {
  caption: string
  children: ReactNode
  className?: string
}

export function DataTableShell({
  children,
  className,
}: {
  children: ReactNode
  className?: string | undefined
}) {
  return <div className={cn('data-table-shell', className)}>{children}</div>
}

export default function DataTable({ caption, children, className }: DataTableProps) {
  return (
    <DataTableShell className={className}>
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </DataTableShell>
  )
}

export function DataTableHead({ children }: { children: ReactNode }) {
  return <thead>{children}</thead>
}

export function DataTableBody({ children }: { children: ReactNode }) {
  return <tbody>{children}</tbody>
}

export function DataTableRow({
  children,
  interactive = true,
}: {
  children: ReactNode
  interactive?: boolean
}) {
  return <tr className={interactive ? 'interactive-row' : undefined}>{children}</tr>
}

export function DataTableHeaderCell({
  children,
  align = 'left',
}: {
  children: ReactNode
  align?: 'left' | 'right'
}) {
  return (
    <th scope="col" className={align === 'right' ? 'text-right' : undefined}>
      {children}
    </th>
  )
}

export function DataTableCell({
  children,
  muted = false,
  className,
}: {
  children: ReactNode
  muted?: boolean
  className?: string
}) {
  return <td className={cn(muted && 'text-muted', className)}>{children}</td>
}
