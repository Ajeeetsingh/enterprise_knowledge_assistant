/**
 * Conversation export — types shared by the format generators, the options
 * dialog, and the export orchestrator.
 *
 * Kept as its own subfolder (`features/chat/export/`) so a future "Share
 * Conversation" feature can sit alongside it and reuse `buildExportModel`
 * without touching the generators.
 */

export type ExportFormat = 'markdown' | 'pdf' | 'text' | 'json'

export interface ExportFormatMeta {
  id: ExportFormat
  label: string
  extension: string
  mimeType: string
  description: string
}

export const EXPORT_FORMATS: ExportFormatMeta[] = [
  {
    id: 'markdown',
    label: 'Markdown (.md)',
    extension: 'md',
    mimeType: 'text/markdown;charset=utf-8',
    description: 'Formatted for docs, wikis, and note apps',
  },
  {
    id: 'pdf',
    label: 'PDF (.pdf)',
    extension: 'pdf',
    mimeType: 'application/pdf',
    description: 'Clean, printable report',
  },
  {
    id: 'text',
    label: 'Plain Text (.txt)',
    extension: 'txt',
    mimeType: 'text/plain;charset=utf-8',
    description: 'Simple readable transcript',
  },
  {
    id: 'json',
    label: 'JSON (.json)',
    extension: 'json',
    mimeType: 'application/json;charset=utf-8',
    description: 'Full structured data with metadata',
  },
]

export function getExportFormatMeta(format: ExportFormat): ExportFormatMeta {
  const meta = EXPORT_FORMATS.find((item) => item.id === format)
  if (!meta) throw new Error(`Unknown export format: ${format}`)
  return meta
}

/**
 * User-facing export toggles. Every format except JSON respects these when
 * rendering; JSON always preserves the full conversation structure (per
 * spec) and only records the requested options as metadata.
 */
export interface ExportOptions {
  includeSources: boolean
  includeConfidence: boolean
  includeTimestamps: boolean
  includeDocumentNames: boolean
}

export const DEFAULT_EXPORT_OPTIONS: ExportOptions = {
  includeSources: true,
  includeConfidence: true,
  includeTimestamps: true,
  includeDocumentNames: true,
}
