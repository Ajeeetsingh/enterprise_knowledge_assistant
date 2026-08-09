import { beforeEach, describe, expect, it } from 'vitest'

import {
  GUEST_CONTINUE_READY_KEY,
  GUEST_STORAGE_KEY,
  GUEST_TRANSITION_KEY,
} from '../constants'
import { saveGuestSession } from './guestSessionStorage'
import {
  armGuestContinuePrompt,
  clearAllGuestDemoState,
  clearGuestImportPending,
  consumeGuestContinuePrompt,
  isGuestImportPending,
  markGuestImportPending,
  shouldOfferGuestContinue,
  shouldPreserveGuestContinueOnAuth,
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

  it('preserves guest continue on auth only from guest demo path', () => {
    markGuestImportPending()
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    expect(shouldPreserveGuestContinueOnAuth('/chat')).toBe(true)
    expect(shouldPreserveGuestContinueOnAuth('/dashboard')).toBe(false)
    expect(shouldPreserveGuestContinueOnAuth(undefined)).toBe(false)
  })

  it('consumeGuestContinuePrompt requires armed ready flag', () => {
    markGuestImportPending()
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    expect(consumeGuestContinuePrompt()).toBe(false)

    armGuestContinuePrompt()
    expect(consumeGuestContinuePrompt()).toBe(true)
    // One-shot — second consume fails even if guest storage remains.
    expect(consumeGuestContinuePrompt()).toBe(false)
  })

  it('clearAllGuestDemoState removes session, transition, and ready keys', () => {
    markGuestImportPending()
    armGuestContinuePrompt()
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    clearAllGuestDemoState()
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeNull()
    expect(sessionStorage.getItem(GUEST_TRANSITION_KEY)).toBeNull()
    expect(sessionStorage.getItem(GUEST_CONTINUE_READY_KEY)).toBeNull()
    expect(shouldOfferGuestContinue()).toBe(false)
  })
})
