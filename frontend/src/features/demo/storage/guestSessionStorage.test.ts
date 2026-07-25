import { beforeEach, describe, expect, it } from 'vitest'

import { GUEST_STORAGE_KEY } from '../constants'
import {
  clearGuestSession,
  loadGuestSession,
  saveGuestSession,
} from './guestSessionStorage'
import { createGuestMessage, emptyGuestSession } from '../types'

describe('guestSessionStorage', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('persists and reloads guest messages and question count', () => {
    const state = emptyGuestSession()
    state.messages = [createGuestMessage('user', 'Hello')]
    state.successfulQuestionCount = 3
    saveGuestSession(state)

    const loaded = loadGuestSession()
    expect(loaded.successfulQuestionCount).toBe(3)
    expect(loaded.messages).toHaveLength(1)
    expect(loaded.messages[0]?.content).toBe('Hello')
  })

  it('resets safely when stored JSON is malformed', () => {
    sessionStorage.setItem(GUEST_STORAGE_KEY, '{not-json')
    const loaded = loadGuestSession()
    expect(loaded.messages).toEqual([])
    expect(loaded.successfulQuestionCount).toBe(0)
  })

  it('resets safely when schema version is unsupported', () => {
    sessionStorage.setItem(
      GUEST_STORAGE_KEY,
      JSON.stringify({ version: 99, messages: [], successfulQuestionCount: 5 }),
    )
    const loaded = loadGuestSession()
    expect(loaded.successfulQuestionCount).toBe(0)
  })

  it('clears stored session', () => {
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hi')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    clearGuestSession()
    expect(sessionStorage.getItem(GUEST_STORAGE_KEY)).toBeNull()
  })
})
