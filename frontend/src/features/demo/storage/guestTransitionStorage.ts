import { GUEST_TRANSITION_KEY } from '../constants'
import { loadGuestSession } from './guestSessionStorage'

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
