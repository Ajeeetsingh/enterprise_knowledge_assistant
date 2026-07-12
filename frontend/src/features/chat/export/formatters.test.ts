import { describe, expect, it } from 'vitest'

import { buildExportFilename, sanitizeFilenameSegment } from './formatters'

describe('sanitizeFilenameSegment', () => {
  it('lowercases and dashes spaces', () => {
    expect(sanitizeFilenameSegment('Remote Work Policy Questions')).toBe(
      'remote-work-policy-questions',
    )
  })

  it('strips unsafe characters', () => {
    expect(sanitizeFilenameSegment('Q&A: "Policy" / Review?!')).toBe('qa-policy-review')
  })

  it('falls back to a default when empty', () => {
    expect(sanitizeFilenameSegment('   ')).toBe('conversation')
  })
})

describe('buildExportFilename', () => {
  it('combines slug, date stamp, and extension', () => {
    const filename = buildExportFilename('Remote Work Policy', 'markdown', '2026-01-05T10:00:00.000Z')
    expect(filename).toBe('remote-work-policy-2026-01-05.md')
  })

  it('uses the correct extension per format', () => {
    expect(buildExportFilename('Title', 'pdf', '2026-01-05T10:00:00.000Z')).toMatch(/\.pdf$/)
    expect(buildExportFilename('Title', 'text', '2026-01-05T10:00:00.000Z')).toMatch(/\.txt$/)
    expect(buildExportFilename('Title', 'json', '2026-01-05T10:00:00.000Z')).toMatch(/\.json$/)
  })
})
