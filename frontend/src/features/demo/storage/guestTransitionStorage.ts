import {
  GUEST_CONTINUE_READY_KEY,
  GUEST_POST_AUTH_PATH,
  GUEST_TRANSITION_KEY,
} from '../constants'
import { clearGuestSession, loadGuestSession } from './guestSessionStorage'

export interface GuestTransitionState {
  version: 1
  pending: true
  setAt: string
}

function isTransitionState(value: unknown): value is GuestTransitionState {
  if (!value || typeof value !== 'object') return false
  const data = value as Record<string, unknown>
  return data.version === 1 && data.pending === true
}

/** Mark that the visitor left the demo intending to possibly continue later. */
export function markGuestImportPending(): void {
  const state: GuestTransitionState = {
    version: 1,
    pending: true,
    setAt: new Date().toISOString(),
  }
  try {
    sessionStorage.setItem(GUEST_TRANSITION_KEY, JSON.stringify(state))
  } catch {
    // ignore quota / private mode
  }
}

export function clearGuestImportPending(): void {
  try {
    sessionStorage.removeItem(GUEST_TRANSITION_KEY)
  } catch {
    // ignore
  }
}

export function isGuestImportPending(): boolean {
  try {
    const raw = sessionStorage.getItem(GUEST_TRANSITION_KEY)
    if (!raw) return false
    const parsed: unknown = JSON.parse(raw)
    return isTransitionState(parsed)
  } catch {
    return false
  }
}

/** True when the user opted into the auth transition and still has guest turns. */
export function shouldOfferGuestContinue(): boolean {
  if (!isGuestImportPending()) return false
  return loadGuestSession().messages.length > 0
}

function clearGuestContinueReady(): void {
  try {
    sessionStorage.removeItem(GUEST_CONTINUE_READY_KEY)
  } catch {
    // ignore
  }
}

/** Clear guest demo conversation + transition/ready flags. */
export function clearAllGuestDemoState(): void {
  clearGuestSession()
  clearGuestImportPending()
  clearGuestContinueReady()
}

/**
 * Arm the one-shot continue prompt after a guest-originated login/register.
 * Must be paired with consumeGuestContinuePrompt() on ChatPage.
 */
export function armGuestContinuePrompt(): void {
  try {
    sessionStorage.setItem(GUEST_CONTINUE_READY_KEY, '1')
  } catch {
    // ignore
  }
}

/**
 * Consume the one-shot ready flag. Returns true only when this auth journey
 * armed the prompt and a migratable guest conversation still exists.
 */
export function consumeGuestContinuePrompt(): boolean {
  try {
    const armed = sessionStorage.getItem(GUEST_CONTINUE_READY_KEY) === '1'
    sessionStorage.removeItem(GUEST_CONTINUE_READY_KEY)
    if (!armed) return false
    return shouldOfferGuestContinue()
  } catch {
    return false
  }
}

/**
 * Whether login/register should preserve guest state and send the user to the
 * continue prompt. Only when the auth page was opened from the guest demo.
 */
export function shouldPreserveGuestContinueOnAuth(from: string | undefined): boolean {
  return from === GUEST_POST_AUTH_PATH && shouldOfferGuestContinue()
}
