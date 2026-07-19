import { DEFAULT_DATE_RANGE_PRESET } from '@/features/analytics/constants'
import type { AnalyticsFilterParams } from '@/features/analytics/types'
import { resolveErrorMessage as resolveErrorMessageWithFallback } from '@/services/errorHandler'

import type { ReportExportRequest, ReportFormatId, ReportModuleId } from '../types'

/** Resolve a user-facing message from a report export failure. */
export function resolveErrorMessage(error: unknown): string {
  return resolveErrorMessageWithFallback(error, 'Unable to export report. Please try again.')
}

/** Translate the analytics date-range filter into a report export request. */
export function buildExportRequest(
  module: ReportModuleId,
  format: ReportFormatId,
  filters: AnalyticsFilterParams,
): ReportExportRequest {
  if (filters.range_preset === 'custom') {
    const request: ReportExportRequest = {
      module,
      format,
      date_range: 'custom',
    }
    if (filters.start_date !== undefined) {
      request.start_date = filters.start_date
    }
    if (filters.end_date !== undefined) {
      request.end_date = filters.end_date
    }
    return request
  }

  return {
    module,
    format,
    date_range: filters.range_preset ?? DEFAULT_DATE_RANGE_PRESET,
  }
}
