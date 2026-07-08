import type { DateRangePreset } from '@/features/analytics/types'

export type ReportModuleId = 'user' | 'ai' | 'knowledge' | 'monitoring' | 'errors'

export type ReportFormatId = 'csv' | 'xlsx' | 'pdf'

export interface ReportModule {
  id: ReportModuleId
  title: string
  description: string
}

export interface ReportFormat {
  id: ReportFormatId
  label: string
  media_type: string
  extension: string
}

export interface ReportExportRequest {
  module: ReportModuleId
  format: ReportFormatId
  date_range?: DateRangePreset
  start_date?: string
  end_date?: string
}

export interface ReportModulesResponse {
  items: ReportModule[]
}

export interface ReportFormatsResponse {
  items: ReportFormat[]
}
