import { useState } from 'react'

import Button from '@/components/ui/Button'
import type { AnalyticsFilterParams } from '@/features/analytics/types'

import type { ReportModuleId } from '../types'
import ExportDialog from './ExportDialog'

export interface AnalyticsExportButtonProps {
  module: ReportModuleId
  filters: AnalyticsFilterParams
}

export default function AnalyticsExportButton({ module, filters }: AnalyticsExportButtonProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="secondary" aria-label="Export analytics report" onClick={() => setOpen(true)}>
        Export
      </Button>
      {open ? (
        <ExportDialog
          open={open}
          onClose={() => setOpen(false)}
          defaultModule={module}
          defaultFilters={filters}
        />
      ) : null}
    </>
  )
}
