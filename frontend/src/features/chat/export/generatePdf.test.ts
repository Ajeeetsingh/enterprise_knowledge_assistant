import { describe, expect, it } from 'vitest'

import { buildExportModel } from './buildExportModel'
import { generatePdfBlob } from './generatePdf'
import { fixtureConversation, fixtureMessages } from './testFixtures'
import { DEFAULT_EXPORT_OPTIONS } from './types'

const now = new Date('2026-01-06T00:00:00.000Z')
const model = buildExportModel(fixtureConversation, fixtureMessages, now)

describe('generatePdfBlob', () => {
  it('produces a non-empty PDF blob for the light theme', () => {
    const blob = generatePdfBlob(model, DEFAULT_EXPORT_OPTIONS, 'light')
    expect(blob.type).toBe('application/pdf')
    expect(blob.size).toBeGreaterThan(0)
  })

  it('produces a non-empty PDF blob for the dark theme', () => {
    const blob = generatePdfBlob(model, DEFAULT_EXPORT_OPTIONS, 'dark')
    expect(blob.type).toBe('application/pdf')
    expect(blob.size).toBeGreaterThan(0)
  })

  it('handles conversations with no citations or long content without throwing', () => {
    const longMessage = {
      ...fixtureMessages[1]!,
      id: 'msg-long',
      content: 'Lorem ipsum dolor sit amet. '.repeat(400),
      citations: [],
    }
    const bigModel = buildExportModel(fixtureConversation, [fixtureMessages[0]!, longMessage], now)
    const blob = generatePdfBlob(bigModel, DEFAULT_EXPORT_OPTIONS, 'light')
    expect(blob.size).toBeGreaterThan(0)
  })
})
