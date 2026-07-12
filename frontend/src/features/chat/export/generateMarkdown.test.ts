import { describe, expect, it } from 'vitest'

import { buildExportModel } from './buildExportModel'
import { generateMarkdown } from './generateMarkdown'
import { fixtureConversation, fixtureMessages } from './testFixtures'
import { DEFAULT_EXPORT_OPTIONS } from './types'

const now = new Date('2026-01-06T00:00:00.000Z')
const model = buildExportModel(fixtureConversation, fixtureMessages, now)

describe('generateMarkdown', () => {
  it('includes the title, roles, content, sources, and confidence by default', () => {
    const markdown = generateMarkdown(model, DEFAULT_EXPORT_OPTIONS)

    expect(markdown).toContain('# Remote work policy questions')
    expect(markdown).toContain('## You')
    expect(markdown).toContain('## Assistant')
    expect(markdown).toContain('What is our remote work policy?')
    expect(markdown).toContain('**Confidence:** 88%')
    expect(markdown).toContain('GTFS-HR-002_Remote_Work_Policy.pdf')
    expect(markdown).toContain('91% confidence')
    expect(markdown).toContain('## Documents Referenced')
  })

  it('uses horizontal separators between exchanges', () => {
    const markdown = generateMarkdown(model, DEFAULT_EXPORT_OPTIONS)
    expect(markdown.match(/^---$/gm)?.length).toBeGreaterThanOrEqual(3)
  })

  it('omits the per-message sources block when includeSources is false', () => {
    const markdown = generateMarkdown(model, { ...DEFAULT_EXPORT_OPTIONS, includeSources: false })
    expect(markdown).not.toContain('**Sources:**')
    // The document names summary section is controlled independently by includeDocumentNames.
    expect(markdown).toContain('## Documents Referenced')
  })

  it('omits both sources and the document names summary when both toggles are off', () => {
    const markdown = generateMarkdown(model, {
      ...DEFAULT_EXPORT_OPTIONS,
      includeSources: false,
      includeDocumentNames: false,
    })
    expect(markdown).not.toContain('**Sources:**')
    expect(markdown).not.toContain('## Documents Referenced')
    expect(markdown).not.toContain('GTFS-HR-002_Remote_Work_Policy.pdf')
  })

  it('omits confidence when includeConfidence is false', () => {
    const markdown = generateMarkdown(model, { ...DEFAULT_EXPORT_OPTIONS, includeConfidence: false })
    expect(markdown).not.toContain('Confidence:')
    expect(markdown).not.toContain('confidence')
  })

  it('omits timestamps when includeTimestamps is false', () => {
    const markdown = generateMarkdown(model, { ...DEFAULT_EXPORT_OPTIONS, includeTimestamps: false })
    expect(markdown).not.toContain('Conversation started')
  })

  it('omits the document names section when includeDocumentNames is false', () => {
    const markdown = generateMarkdown(model, { ...DEFAULT_EXPORT_OPTIONS, includeDocumentNames: false })
    expect(markdown).not.toContain('## Documents Referenced')
  })
})
