import { conversationDisplayTitle, type Conversation, type Message } from '../types'

/**
 * Normalized, format-agnostic representation of a conversation ready for
 * export. Every generator (Markdown/PDF/Text/JSON) reads from this single
 * model instead of the raw API types, so a future "Share Conversation"
 * feature can build the same model and hand it to whichever renderer it
 * needs.
 */
export interface ExportCitationModel {
  source: string
  page: number | null
  confidence: number
  excerpt: string
}

export interface ExportMessageModel {
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAtIso: string
  confidenceScore: number | null
  citations: ExportCitationModel[]
}

export interface ExportConversationModel {
  conversationId: string
  title: string
  createdAtIso: string
  updatedAtIso: string
  exportedAtIso: string
  messages: ExportMessageModel[]
  /** Unique source document names referenced by any citation, in first-seen order. */
  documentNames: string[]
}

export function buildExportModel(
  conversation: Conversation,
  messages: Message[],
  now: Date = new Date(),
): ExportConversationModel {
  const documentNames: string[] = []
  const seen = new Set<string>()

  const exportMessages: ExportMessageModel[] = messages.map((message) => {
    const citations: ExportCitationModel[] = message.citations.map((citation) => {
      if (!seen.has(citation.source)) {
        seen.add(citation.source)
        documentNames.push(citation.source)
      }
      return {
        source: citation.source,
        page: citation.page ?? null,
        confidence: citation.confidence,
        excerpt: citation.excerpt,
      }
    })

    return {
      role: message.role,
      content: message.content,
      createdAtIso: message.created_at,
      confidenceScore: message.confidence_score,
      citations,
    }
  })

  return {
    conversationId: conversation.id,
    title: conversationDisplayTitle(conversation),
    createdAtIso: conversation.created_at,
    updatedAtIso: conversation.updated_at,
    exportedAtIso: now.toISOString(),
    messages: exportMessages,
    documentNames,
  }
}
