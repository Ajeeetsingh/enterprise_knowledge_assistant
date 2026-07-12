import { describe, expect, it } from 'vitest'

import { buildExportModel } from './buildExportModel'
import { generateJson } from './generateJson'
import { fixtureConversation, fixtureMessages } from './testFixtures'
import { DEFAULT_EXPORT_OPTIONS } from './types'

const now = new Date('2026-01-06T00:00:00.000Z')
const model = buildExportModel(fixtureConversation, fixtureMessages, now)

describe('generateJson', () => {
  it('is valid, pretty-printed JSON', () => {
    const json = generateJson(model, DEFAULT_EXPORT_OPTIONS)
    expect(() => JSON.parse(json)).not.toThrow()
    expect(json).toContain('\n  ')
  })

  it('always preserves the full structure regardless of options', () => {
    const restrictiveOptions = {
      includeSources: false,
      includeConfidence: false,
      includeTimestamps: false,
      includeDocumentNames: false,
    }
    const json = generateJson(model, restrictiveOptions)
    const parsed = JSON.parse(json) as {
      messages: Array<{ citations: unknown[]; confidenceScore: number | null }>
      documentNames: string[]
      exportedWithOptions: typeof restrictiveOptions
    }

    expect(parsed.messages[1]!.citations).toHaveLength(2)
    expect(parsed.messages[1]!.confidenceScore).toBe(0.88)
    expect(parsed.documentNames).toHaveLength(2)
    expect(parsed.exportedWithOptions).toEqual(restrictiveOptions)
  })
})
