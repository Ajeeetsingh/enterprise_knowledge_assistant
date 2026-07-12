import { formatConfidencePercent, formatExportDateTime } from './formatters'
import type { ExportConversationModel, ExportMessageModel } from './buildExportModel'
import type { ExportOptions } from './types'

function roleHeading(role: ExportMessageModel['role']): string {
  if (role === 'user') return 'You'
  if (role === 'assistant') return 'Assistant'
  return 'System'
}

function renderCitations(message: ExportMessageModel, options: ExportOptions): string[] {
  if (!options.includeSources || message.citations.length === 0) return []

  const lines = ['**Sources:**', '']
  message.citations.forEach((citation, index) => {
    const pageLabel = citation.page != null ? `, p. ${citation.page}` : ''
    const confidenceLabel = options.includeConfidence
      ? ` — ${formatConfidencePercent(citation.confidence)} confidence`
      : ''
    lines.push(`${index + 1}. **${citation.source}**${pageLabel}${confidenceLabel}`)
    if (citation.excerpt.trim()) {
      lines.push(`   > ${citation.excerpt.trim().replace(/\n+/g, ' ')}`)
    }
  })
  return lines
}

function renderMessage(message: ExportMessageModel, options: ExportOptions): string {
  const lines: string[] = [`## ${roleHeading(message.role)}`, '']

  if (options.includeTimestamps) {
    lines.push(`*${formatExportDateTime(message.createdAtIso)}*`, '')
  }

  lines.push(message.content.trim(), '')

  if (message.role === 'assistant' && options.includeConfidence && message.confidenceScore != null) {
    lines.push(`**Confidence:** ${formatConfidencePercent(message.confidenceScore)}`, '')
  }

  const citationLines = renderCitations(message, options)
  if (citationLines.length > 0) {
    lines.push(...citationLines, '')
  }

  return lines.join('\n')
}

export function generateMarkdown(model: ExportConversationModel, options: ExportOptions): string {
  const sections: string[] = [`# ${model.title}`, '']

  sections.push(`*Exported ${formatExportDateTime(model.exportedAtIso)}*`)
  if (options.includeTimestamps) {
    sections.push(`*Conversation started ${formatExportDateTime(model.createdAtIso)}*`)
  }
  sections.push('')

  if (options.includeDocumentNames && model.documentNames.length > 0) {
    sections.push('---', '', '## Documents Referenced', '')
    model.documentNames.forEach((name) => sections.push(`- ${name}`))
    sections.push('')
  }

  model.messages.forEach((message) => {
    sections.push('---', '', renderMessage(message, options))
  })

  sections.push('---')

  return sections.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n'
}
