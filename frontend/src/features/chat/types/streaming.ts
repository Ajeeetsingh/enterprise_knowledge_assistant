import type { Citation } from '@/features/chat/types'

/** Ephemeral frontend-only streaming session (Phase 10.0.3). */
export interface ActiveStream {
  conversationId: string
  content: string
  citations: Citation[]
  confidence_score: number | null
}

export function shouldHidePersistedAssistantMessage(
  messages: Array<{ role: string; content: string }>,
  activeStream: ActiveStream | null,
): boolean {
  if (!activeStream) return false

  const lastMessage = messages[messages.length - 1]
  return (
    lastMessage?.role === 'assistant' && lastMessage.content === activeStream.content
  )
}

export function getMessagesForDisplay<T extends { role: string; content: string }>(
  messages: T[],
  activeStream: ActiveStream | null,
): T[] {
  if (!shouldHidePersistedAssistantMessage(messages, activeStream)) {
    return messages
  }

  return messages.slice(0, -1)
}
