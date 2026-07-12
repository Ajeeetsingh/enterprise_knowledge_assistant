import type { ExportFormat } from './types'
import { getExportFormatMeta } from './types'

/** e.g. "Jan 5, 2026, 3:45 PM" — used across all four export formats. */
export function formatExportDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** e.g. "2026-01-05" — used for filenames. */
export function formatExportDateStamp(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'export'
  return date.toISOString().slice(0, 10)
}

/** Strips characters that are unsafe/awkward in filenames across OSes. */
export function sanitizeFilenameSegment(value: string): string {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  return cleaned || 'conversation'
}

export function buildExportFilename(title: string, format: ExportFormat, exportedAtIso: string): string {
  const { extension } = getExportFormatMeta(format)
  const slug = sanitizeFilenameSegment(title)
  const stamp = formatExportDateStamp(exportedAtIso)
  return `${slug}-${stamp}.${extension}`
}

export function formatConfidencePercent(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}
