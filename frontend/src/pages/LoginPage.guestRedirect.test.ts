import { beforeEach, describe, expect, it } from 'vitest'

import { resolveRedirectPath } from '@/pages/LoginPage'
import { markGuestImportPending } from '@/features/demo'
import { saveGuestSession } from '@/features/demo/storage/guestSessionStorage'
import { createGuestMessage } from '@/features/demo/types'

describe('LoginPage resolveRedirectPath with guest transition', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('redirects to /chat when guest continue is pending', () => {
    markGuestImportPending()
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    expect(resolveRedirectPath('/dashboard')).toBe('/chat')
    expect(resolveRedirectPath(undefined)).toBe('/chat')
  })

  it('uses default dashboard when no guest continue is pending', () => {
    expect(resolveRedirectPath(undefined)).toBe('/dashboard')
    expect(resolveRedirectPath('/documents')).toBe('/documents')
  })
})
