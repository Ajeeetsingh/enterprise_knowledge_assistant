import { useMutation } from '@tanstack/react-query'

import { exportReport } from '../services/reportsApi'
import type { ReportExportRequest } from '../types'

export function useExportReport() {
  return useMutation({
    mutationFn: (request: ReportExportRequest) => exportReport(request),
  })
}
