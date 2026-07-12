import { describe, expect, it } from 'vitest'

import { buildExportModel } from './buildExportModel'
import { generateText } from './generateText'
import { fixtureConversation, fixtureMessages } from './testFixtures'
import { DEFAULT_EXPORT_OPTIONS } from './types'

const now = new Date('2026-01-06T00:00:00.000Z')
const model = buildExportModel(fixtureConversation, fixtureMessages, now)

describe('generateText', () => {
  it('renders a readable plain-text transcript', () => {
    const text = generateText(model, DEFAULT_EXPORT_OPTIONS)
    expect(text).toContain('ENTERPRISE KNOWLEDGE ASSISTANT')
    expect(text).toContain('Title: Remote work policy questions')
    expect(text).toContain('You')
    expect(text).toContain('Assistant')
    expect(text).toContain('What is our remote work policy?')
    expect(text).toContain('Confidence: 88%')
    expect(text).toContain('Documents Referenced:')
  })

  it('respects the include toggles', () => {
    const text = generateText(model, {
      includeSources: false,
      includeConfidence: false,
      includeTimestamps: false,
      includeDocumentNames: false,
    })
    expect(text).not.toContain('Sources:')
    expect(text).not.toContain('Confidence:')
    expect(text).not.toContain('Started:')
    expect(text).not.toContain('Documents Referenced:')
  })
})
