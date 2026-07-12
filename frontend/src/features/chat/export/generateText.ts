import { formatConfidencePercent, formatExportDateTime } from './formatters'
import type { ExportConversationModel, ExportMessageModel } from './buildExportModel'
import type { ExportOptions } from './types'

const RULE = '-'.repeat(56)

function roleLabel(role: ExportMessageModel['role']): string {
  if (role === 'user') return 'You'
  if (role === 'assistant') return 'Assistant'
  return 'System'
}

function renderMessage(message: ExportMessageModel, options: ExportOptions): string[] {
  const lines: string[] = []
  const label = roleLabel(message.role)
  const timestamp = options.includeTimestamps ? ` (${formatExportDateTime(message.createdAtIso)})` : ''
  lines.push(`${label}${timestamp}:`)
  lines.push(message.content.trim())

  if (message.role === 'assistant' && options.includeConfidence && message.confidenceScore != null) {
    lines.push(`Confidence: ${formatConfidencePercent(message.confidenceScore)}`)
  }

  if (options.includeSources && message.citations.length > 0) {
    lines.push('Sources:')
    message.citations.forEach((citation) => {
      const pageLabel = citation.page != null ? `, p. ${citation.page}` : ''
      const confidenceLabel = options.includeConfidence
        ? `, ${formatConfidencePercent(citation.confidence)} confidence`
        : ''
      lines.push(`  - ${citation.source}${pageLabel}${confidenceLabel}`)
    })
  }

  return lines
}

export function generateText(model: ExportConversationModel, options: ExportOptions): string {
  const lines: string[] = []
  lines.push('ENTERPRISE KNOWLEDGE ASSISTANT — CONVERSATION EXPORT')
  lines.push(RULE)
  lines.push(`Title: ${model.title}`)
  lines.push(`Exported: ${formatExportDateTime(model.exportedAtIso)}`)
  if (options.includeTimestamps) {
    lines.push(`Started: ${formatExportDateTime(model.createdAtIso)}`)
  }

  if (options.includeDocumentNames && model.documentNames.length > 0) {
    lines.push('')
    lines.push('Documents Referenced:')
    model.documentNames.forEach((name) => lines.push(`  - ${name}`))
  }

  model.messages.forEach((message) => {
    lines.push('')
    lines.push(RULE)
    lines.push('')
    lines.push(...renderMessage(message, options))
  })

  lines.push('')
  lines.push(RULE)

  return lines.join('\n') + '\n'
}
