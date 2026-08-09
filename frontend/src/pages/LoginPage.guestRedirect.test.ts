import { beforeEach, describe, expect, it } from 'vitest'

import { resolveRedirectPath } from '@/pages/LoginPage'
import { markGuestImportPending } from '@/features/demo'
import { saveGuestSession } from '@/features/demo/storage/guestSessionStorage'
import { createGuestMessage } from '@/features/demo/types'

describe('LoginPage resolveRedirectPath with guest transition', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('does not hijack redirect based on stale guest storage alone', () => {
    markGuestImportPending()
    saveGuestSession({
      version: 1,
      messages: [createGuestMessage('user', 'Hello')],
      successfulQuestionCount: 1,
      updatedAt: new Date().toISOString(),
    })
    expect(resolveRedirectPath('/dashboard')).toBe('/dashboard')
    expect(resolveRedirectPath(undefined)).toBe('/dashboard')
  })

  it('uses default dashboard when no from path is provided', () => {
    expect(resolveRedirectPath(undefined)).toBe('/dashboard')
    expect(resolveRedirectPath('/documents')).toBe('/documents')
  })
})
