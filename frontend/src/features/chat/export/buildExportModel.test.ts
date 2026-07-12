import { describe, expect, it } from 'vitest'

import { buildExportModel } from './buildExportModel'
import { fixtureConversation, fixtureMessages } from './testFixtures'

describe('buildExportModel', () => {
  const now = new Date('2026-01-06T00:00:00.000Z')

  it('carries over conversation identity and title', () => {
    const model = buildExportModel(fixtureConversation, fixtureMessages, now)
    expect(model.conversationId).toBe('conv-1')
    expect(model.title).toBe('Remote work policy questions')
    expect(model.createdAtIso).toBe(fixtureConversation.created_at)
    expect(model.exportedAtIso).toBe(now.toISOString())
  })

  it('maps every message with its citations', () => {
    const model = buildExportModel(fixtureConversation, fixtureMessages, now)
    expect(model.messages).toHaveLength(2)
    expect(model.messages[0]!.role).toBe('user')
    expect(model.messages[1]!.citations).toHaveLength(2)
    expect(model.messages[1]!.confidenceScore).toBe(0.88)
  })

  it('collects unique document names in first-seen order', () => {
    const model = buildExportModel(fixtureConversation, fixtureMessages, now)
    expect(model.documentNames).toEqual([
      'GTFS-HR-002_Remote_Work_Policy.pdf',
      'GTFS-HR-001_Employee_Handbook.pdf',
    ])
  })

  it('deduplicates document names referenced by multiple citations', () => {
    const repeatedMessages = [
      ...fixtureMessages,
      { ...fixtureMessages[1]!, id: 'msg-3' },
    ]
    const model = buildExportModel(fixtureConversation, repeatedMessages, now)
    expect(model.documentNames).toHaveLength(2)
  })

  it('falls back to the generated display title when conversation has no title', () => {
    const model = buildExportModel({ ...fixtureConversation, title: null }, fixtureMessages, now)
    expect(model.title).toContain('Conversation')
  })
})
