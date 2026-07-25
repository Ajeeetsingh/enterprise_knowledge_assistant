import type { Message, MessageRole } from '@/features/chat/types'

export interface GuestMessage extends Message {
  /** When true, UI should offer a Sign In action for this assistant turn. */
  requiresAuth?: boolean
  answerKind?: string | null
}

export interface GuestSessionState {
  version: 1
  messages: GuestMessage[]
  successfulQuestionCount: number
  updatedAt: string
}

export function createGuestMessage(
  role: MessageRole,
  content: string,
  extras: Pick<GuestMessage, 'requiresAuth' | 'answerKind'> = {},
): GuestMessage {
  const message: GuestMessage = {
    id: crypto.randomUUID(),
    role,
    content,
    citations: [],
    confidence_score: null,
    created_at: new Date().toISOString(),
  }
  if (extras.requiresAuth !== undefined) {
    message.requiresAuth = extras.requiresAuth
  }
  if (extras.answerKind !== undefined) {
    message.answerKind = extras.answerKind
  }
  return message
}

export function emptyGuestSession(): GuestSessionState {
  return {
    version: 1,
    messages: [],
    successfulQuestionCount: 0,
    updatedAt: new Date().toISOString(),
  }
}
