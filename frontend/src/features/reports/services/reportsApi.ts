import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  ReportExportRequest,
  ReportFormatsResponse,
  ReportModulesResponse,
} from '../types'

const BASE_PATH = '/admin/reports'

function parseFilename(contentDisposition: string | undefined, fallback: string): string {
  if (!contentDisposition) {
    return fallback
  }
  const match = /filename="([^"]+)"/.exec(contentDisposition)
  return match?.[1] ?? fallback
}

export async function getReportModules(): Promise<ReportModulesResponse> {
  try {
    const { data } = await apiClient.get<ReportModulesResponse>(`${BASE_PATH}/modules`)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getReportFormats(): Promise<ReportFormatsResponse> {
  try {
    const { data } = await apiClient.get<ReportFormatsResponse>(`${BASE_PATH}/formats`)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}

export async function exportReport(
  request: ReportExportRequest,
): Promise<{ blob: Blob; filename: string }> {
  try {
    const response = await apiClient.post(`${BASE_PATH}/export`, request, {
      responseType: 'blob',
    })
    const fallbackExtension = request.format === 'xlsx' ? 'xlsx' : request.format
    const filename = parseFilename(
      response.headers['content-disposition'],
      `${request.module}_report.${fallbackExtension}`,
    )
    return { blob: response.data as Blob, filename }
  } catch (error) {
    throw toApiError(error)
  }
}

export function downloadReportFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
