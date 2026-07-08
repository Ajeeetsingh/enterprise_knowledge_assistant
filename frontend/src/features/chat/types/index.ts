/**
 * Chat feature types — aligned with backend conversation and chat APIs.
 */

export interface Conversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
}

export interface ConversationCreateRequest {
  title?: string | null
}

export interface ConversationUpdateRequest {
  title: string
}

export interface ConversationDeleteResponse {
  id: string
  message: string
}

export interface Citation {
  source: string
  excerpt: string
  confidence: number
  page?: number | null
  metadata?: Record<string, unknown>
}

export interface CitationDetails {
  source: string
  excerpt: string | null
  confidence: number
  page: number | null
  metadata?: Record<string, unknown>
}

export function formatCitationConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  citations: Citation[]
  confidence_score: number | null
  created_at: string
}

export interface ConversationHistoryResponse {
  items: Message[]
}

export interface ChatRequest {
  conversation_id: string
  question: string
}

export interface ChatResponse {
  conversation_id: string
  answer: string
  confidence_score: number
  citations: Citation[]
  message: string
}

/** Normalise citation objects returned on message history records. */
export function normalizeCitation(value: unknown): Citation | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  if (typeof record.source !== 'string' || typeof record.excerpt !== 'string') {
    return null
  }
  return {
    source: record.source,
    excerpt: record.excerpt,
    confidence: typeof record.confidence === 'number' ? record.confidence : 0,
    page: typeof record.page === 'number' ? record.page : null,
    ...(record.metadata && typeof record.metadata === 'object'
      ? { metadata: record.metadata as Record<string, unknown> }
      : {}),
  }
}

export function normalizeMessageCitations(raw: unknown): Citation[] {
  if (!Array.isArray(raw)) return []
  return raw.map(normalizeCitation).filter((item): item is Citation => item !== null)
}

export function conversationDisplayTitle(conversation: Conversation): string {
  if (conversation.title?.trim()) return conversation.title.trim()
  return `Conversation ${new Date(conversation.created_at).toLocaleDateString()}`
}
