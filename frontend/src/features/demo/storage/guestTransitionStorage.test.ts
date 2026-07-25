import { beforeEach, describe, expect, it } from 'vitest'

import { GUEST_TRANSITION_KEY } from '../constants'
import { saveGuestSession } from './guestSessionStorage'
import {
  clearGuestImportPending,
  isGuestImportPending,
  markGuestImportPending,
  shouldOfferGuestContinue,
} from './guestTransitionStorage'
import { createGuestMessage, emptyGuestSession } from '../types'

describe('guestTransitionStorage', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('marks and clears pending transition intent', () => {
    markGuestImportPending()
    expect(isGuestImportPending()).toBe(true)
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeTruthy()
    clearGuestImportPending()
    expect(isGuestImportPending()).toBe(false)
  })

  it('offers continue only when pending and guest messages exist', () => {
    markGuestImportPending()
    expect(shouldOfferGuestContinue()).toBe(false)

    const state = emptyGuestSession()
    state.messages = [createGuestMessage('user', 'Hello')]
    saveGuestSession(state)
    expect(shouldOfferGuestContinue()).toBe(true)
  })

  it('does not offer continue without pending intent', () => {
    const state = emptyGuestSession()
    state.messages = [createGuestMessage('user', 'Hello')]
    saveGuestSession(state)
    expect(shouldOfferGuestContinue()).toBe(false)
  })
})
