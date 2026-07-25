import {
  GUEST_STORAGE_KEY,
  GUEST_STORAGE_MAX_MESSAGES,
} from '../constants'
import {
  emptyGuestSession,
  type GuestMessage,
  type GuestSessionState,
} from '../types'

function isGuestMessage(value: unknown): value is GuestMessage {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return (
    typeof item.id === 'string' &&
    (item.role === 'user' || item.role === 'assistant' || item.role === 'system') &&
    typeof item.content === 'string' &&
    Array.isArray(item.citations)
  )
}

function sanitizeState(raw: unknown): GuestSessionState | null {
  if (!raw || typeof raw !== 'object') return null
  const data = raw as Record<string, unknown>
  if (data.version !== 1) return null
  if (!Array.isArray(data.messages)) return null
  if (typeof data.successfulQuestionCount !== 'number') return null

  const messages = data.messages.filter(isGuestMessage).slice(-GUEST_STORAGE_MAX_MESSAGES)
  const successfulQuestionCount = Math.max(
    0,
    Math.min(10_000, Math.floor(data.successfulQuestionCount)),
  )

  return {
    version: 1,
    messages,
    successfulQuestionCount,
    updatedAt:
      typeof data.updatedAt === 'string' ? data.updatedAt : new Date().toISOString(),
  }
}

export function loadGuestSession(): GuestSessionState {
  try {
    const raw = sessionStorage.getItem(GUEST_STORAGE_KEY)
    if (!raw) return emptyGuestSession()
    const parsed: unknown = JSON.parse(raw)
    return sanitizeState(parsed) ?? emptyGuestSession()
  } catch {
    return emptyGuestSession()
  }
}

export function saveGuestSession(state: GuestSessionState): void {
  const next: GuestSessionState = {
    version: 1,
    messages: state.messages.slice(-GUEST_STORAGE_MAX_MESSAGES),
    successfulQuestionCount: state.successfulQuestionCount,
    updatedAt: new Date().toISOString(),
  }
  try {
    sessionStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Quota or private mode — keep in-memory only.
  }
}

export function clearGuestSession(): void {
  try {
    sessionStorage.removeItem(GUEST_STORAGE_KEY)
  } catch {
    // ignore
  }
}
