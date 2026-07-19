import { describe, expect, it } from 'vitest'

import {
  buildNormalizedIndexMap,
  findCitationMatchInPage,
  normalizeForMatch,
} from './matchCitationText'

describe('normalizeForMatch', () => {
  it('collapses whitespace and lowercases', () => {
    expect(normalizeForMatch('  Hello\n\nWorld  ')).toBe('hello world')
  })
})

describe('findCitationMatchInPage', () => {
  it('finds an exact normalized match', () => {
    const page =
      'Employees are entitled to 20 days of annual leave each calendar year.'
    const citation = 'Employees are entitled to 20 days of annual leave'
    const match = findCitationMatchInPage(page, citation)
    expect(match).not.toBeNull()
    expect(page.slice(match!.start, match!.end)).toContain('Employees are entitled')
  })

  it('matches across line breaks and repeated spaces', () => {
    const page = 'Remote  work\nis permitted\n\nup to three days per week.'
    const citation = 'Remote work is permitted up to three days per week.'
    const match = findCitationMatchInPage(page, citation)
    expect(match).not.toBeNull()
  })

  it('matches multi-line citation text against flattened page text', () => {
    const page =
      'Section 4.2 Leave Policy. Full-time staff receive twenty days of paid annual leave. Part-time staff receive a pro-rated entitlement.'
    const citation =
      'Full-time staff receive twenty days of paid annual leave.\nPart-time staff receive a pro-rated entitlement.'
    const match = findCitationMatchInPage(page, citation)
    expect(match).not.toBeNull()
    expect(page.slice(match!.start, match!.end).toLowerCase()).toContain('full-time staff')
  })

  it('falls back to a distinctive subsection when the full excerpt is absent', () => {
    const page =
      'The reimbursement window closes on the last business day of each month for travel expenses submitted through the portal.'
    const citation =
      'PREFIX NOT ON PAGE. The reimbursement window closes on the last business day of each month for travel expenses submitted through the portal. SUFFIX ALSO MISSING.'
    const match = findCitationMatchInPage(page, citation)
    expect(match).not.toBeNull()
    expect(page.slice(match!.start, match!.end).toLowerCase()).toContain('reimbursement window')
  })

  it('returns null when nothing distinctive matches', () => {
    const page = 'Completely unrelated policy text about parking permits.'
    const citation =
      'Employees are entitled to twenty days of annual leave each calendar year under this handbook.'
    expect(findCitationMatchInPage(page, citation)).toBeNull()
  })

  it('avoids highlighting short generic words alone', () => {
    const page = 'The the the policy applies to all staff in the company.'
    expect(findCitationMatchInPage(page, 'the')).toBeNull()
  })
})

describe('buildNormalizedIndexMap', () => {
  it('maps normalized indices back to raw character positions', () => {
    const { normalized, normToRaw } = buildNormalizedIndexMap('A  B\nC')
    expect(normalized).toBe('a b c')
    expect(normToRaw).toHaveLength(normalized.length)
  })
})
