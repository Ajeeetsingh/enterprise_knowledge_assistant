import { triggerBlobDownload } from '@/utils/downloadBlob'

import type { Conversation, Message } from '../types'
import { buildExportModel } from './buildExportModel'
import { buildExportFilename } from './formatters'
import { generateJson } from './generateJson'
import { generateMarkdown } from './generateMarkdown'
import { generatePdfBlob } from './generatePdf'
import { generateText } from './generateText'
import { getExportFormatMeta, type ExportFormat, type ExportOptions } from './types'

export interface ExportConversationParams {
  conversation: Conversation
  messages: Message[]
  format: ExportFormat
  options: ExportOptions
  /** Only affects PDF rendering — the other formats are theme-agnostic plain text. */
  theme: 'light' | 'dark'
  now?: Date
}

export interface ExportConversationResult {
  filename: string
  format: ExportFormat
}

/**
 * Builds the export model, renders it with the format-specific generator,
 * and immediately triggers a browser download. Fully client-side — no
 * network request is made, so this works offline and needs no backend
 * support.
 */
export function exportConversation({
  conversation,
  messages,
  format,
  options,
  theme,
  now = new Date(),
}: ExportConversationParams): ExportConversationResult {
  const model = buildExportModel(conversation, messages, now)
  const { mimeType } = getExportFormatMeta(format)
  const filename = buildExportFilename(model.title, format, model.exportedAtIso)

  const blob =
    format === 'pdf'
      ? generatePdfBlob(model, options, theme)
      : new Blob([renderTextualFormat(format, model, options)], { type: mimeType })

  triggerBlobDownload(blob, filename)

  return { filename, format }
}

function renderTextualFormat(
  format: Exclude<ExportFormat, 'pdf'>,
  model: ReturnType<typeof buildExportModel>,
  options: ExportOptions,
): string {
  switch (format) {
    case 'markdown':
      return generateMarkdown(model, options)
    case 'text':
      return generateText(model, options)
    case 'json':
      return generateJson(model, options)
    default:
      return ''
  }
}
