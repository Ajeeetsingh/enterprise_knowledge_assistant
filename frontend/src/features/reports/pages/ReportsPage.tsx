import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Spinner from '@/components/ui/Spinner'
import { DEFAULT_DATE_RANGE_PRESET } from '@/features/analytics/constants'
import type { AnalyticsFilterParams } from '@/features/analytics/types'
import { useToast } from '@/contexts/ToastContext'
import type { ApiError } from '@/types'

import {
  DateRangeSelector,
  ExportHistory,
  ModuleSelector,
  ReportFormatSelector,
} from '../components'
import { useExportReport, useReportFormats, useReportModules } from '../hooks'
import { downloadReportFile } from '../services/reportsApi'
import type { ReportExportRequest, ReportFormatId, ReportModuleId } from '../types'

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

export default function ReportsPage() {
  const { showSuccess, showError } = useToast()
  const modulesQuery = useReportModules()
  const formatsQuery = useReportFormats()
  const exportMutation = useExportReport()

  const [module, setModule] = useState<ReportModuleId>('user')
  const [format, setFormat] = useState<ReportFormatId>('pdf')
  const [filters, setFilters] = useState<AnalyticsFilterParams>({
    range_preset: DEFAULT_DATE_RANGE_PRESET,
  })

  const modules = useMemo(() => modulesQuery.data?.items ?? [], [modulesQuery.data?.items])
  const formats = useMemo(() => formatsQuery.data?.items ?? [], [formatsQuery.data?.items])
  const selectedModule = modules.find((item) => item.id === module)
  const isLoading = modulesQuery.isLoading || formatsQuery.isLoading

  async function handleExport() {
    try {
      const { blob, filename } = await exportMutation.mutateAsync(
        buildExportRequest(module, format, filters),
      )
      downloadReportFile(blob, filename)
      showSuccess('Report downloaded successfully.')
    } catch (error) {
      showError(resolveErrorMessage(error))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Reporting & Export
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Export analytics dashboards for operational reviews, compliance, and executive reporting.
        </p>
      </div>

      <Card className="flex flex-col gap-5">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
            <Spinner size="sm" label="Loading report options" />
            Loading report options…
          </div>
        ) : (
          <>
            <ModuleSelector modules={modules} value={module} onChange={setModule} />
            {selectedModule ? (
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {selectedModule.description}
              </p>
            ) : null}
            <DateRangeSelector filters={filters} onChange={setFilters} />
            <ReportFormatSelector formats={formats} value={format} onChange={setFormat} />
            <div>
              <Button isLoading={exportMutation.isPending} onClick={() => void handleExport()}>
                Download Report
              </Button>
            </div>
          </>
        )}
      </Card>

      <ExportHistory />
    </div>
  )
}
