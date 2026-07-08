import { useEffect, useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { DEFAULT_DATE_RANGE_PRESET } from '@/features/analytics/constants'
import type { AnalyticsFilterParams } from '@/features/analytics/types'
import { useToast } from '@/contexts/ToastContext'
import type { ApiError } from '@/types'

import { useExportReport, useReportFormats, useReportModules } from '../hooks'
import { downloadReportFile } from '../services/reportsApi'
import type { ReportExportRequest, ReportFormatId, ReportModuleId } from '../types'
import DateRangeSelector from './DateRangeSelector'
import ModuleSelector from './ModuleSelector'
import ReportFormatSelector from './ReportFormatSelector'

export interface ExportDialogProps {
  open: boolean
  onClose: () => void
  defaultModule?: ReportModuleId
  defaultFilters?: AnalyticsFilterParams
}

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Unable to export report. Please try again.'
}

function buildExportRequest(
  module: ReportModuleId,
  format: ReportFormatId,
  filters: AnalyticsFilterParams,
): ReportExportRequest {
  if (filters.range_preset === 'custom') {
    return {
      module,
      format,
      date_range: 'custom',
      start_date: filters.start_date,
      end_date: filters.end_date,
    }
  }

  return {
    module,
    format,
    date_range: filters.range_preset ?? DEFAULT_DATE_RANGE_PRESET,
  }
}

export default function ExportDialog({
  open,
  onClose,
  defaultModule = 'user',
  defaultFilters,
}: ExportDialogProps) {
  const { showSuccess, showError } = useToast()
  const modulesQuery = useReportModules()
  const formatsQuery = useReportFormats()
  const exportMutation = useExportReport()

  const [module, setModule] = useState<ReportModuleId>(defaultModule)
  const [format, setFormat] = useState<ReportFormatId>('pdf')
  const [filters, setFilters] = useState<AnalyticsFilterParams>(
    defaultFilters ?? { range_preset: DEFAULT_DATE_RANGE_PRESET },
  )

  useEffect(() => {
    if (!open) {
      return
    }
    setModule(defaultModule)
    setFilters(defaultFilters ?? { range_preset: DEFAULT_DATE_RANGE_PRESET })
  }, [open, defaultModule, defaultFilters])

  const modules = useMemo(() => modulesQuery.data?.items ?? [], [modulesQuery.data?.items])
  const formats = useMemo(() => formatsQuery.data?.items ?? [], [formatsQuery.data?.items])

  useEffect(() => {
    if (formats.length > 0 && !formats.some((item) => item.id === format)) {
      setFormat(formats[0].id)
    }
  }, [format, formats])

  if (!open) {
    return null
  }

  async function handleExport() {
    try {
      const request = buildExportRequest(module, format, filters)
      const { blob, filename } = await exportMutation.mutateAsync(request)
      downloadReportFile(blob, filename)
      showSuccess('Report downloaded successfully.')
      onClose()
    } catch (error) {
      showError(resolveErrorMessage(error))
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/50 p-4"
      role="presentation"
      onClick={onClose}
    >
      <Card
        className="w-full max-w-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex flex-col gap-5">
          <div>
            <h2
              id="export-dialog-title"
              className="text-xl font-semibold text-neutral-900 dark:text-neutral-50"
            >
              Export Analytics Report
            </h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              Choose a module, date range, and format to download a management-ready report.
            </p>
          </div>

          <ModuleSelector
            modules={modules}
            value={module}
            onChange={setModule}
            isLoading={modulesQuery.isLoading}
          />

          <DateRangeSelector filters={filters} onChange={setFilters} />

          <ReportFormatSelector
            formats={formats}
            value={format}
            onChange={setFormat}
            isLoading={formatsQuery.isLoading}
          />

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              isLoading={exportMutation.isPending}
              disabled={modulesQuery.isLoading || formatsQuery.isLoading}
              onClick={() => {
                void handleExport()
              }}
            >
              Download Report
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
